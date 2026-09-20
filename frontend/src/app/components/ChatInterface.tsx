import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, ThumbsUp, ThumbsDown, MapPin, Phone, Mail, Globe, AlertCircle } from "lucide-react";
import {
  ask,
  getPublicConfig,
  sendFeedback,
  errorMessage,
  type AskResponse,
  type DocumentExtract,
  type OrganizationResult,
} from "../lib/api";

interface Message {
  id: string;
  type: "user" | "bot" | "error";
  content: string;
  timestamp: Date;
  suggestions?: string[];
  organizations?: OrganizationResult[];
  documents?: DocumentExtract[];
  queryId?: number | null;
  feedback?: boolean | null;
  answered?: boolean;
}

const LOADING_MESSAGE: Message = {
  id: "0",
  type: "bot",
  content: "Connexion au service...",
  timestamp: new Date(),
};

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([LOADING_MESSAGE]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [botName, setBotName] = useState("Assistant Grand Albigeois");
  const [online, setOnline] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Message d'accueil, nom et suggestions initiales : tout vient de GET /config,
  // donc l'administrateur les change depuis le back-office sans toucher au code.
  useEffect(() => {
    let cancelled = false;
    getPublicConfig()
      .then((config) => {
        if (cancelled) return;
        setBotName(config.name);
        setOnline(true);
        setMessages([
          {
            id: "0",
            type: "bot",
            content: config.welcome_message,
            timestamp: new Date(),
            suggestions: config.initial_suggestions,
          },
        ]);
      })
      .catch((error) => {
        if (cancelled) return;
        setOnline(false);
        setMessages([
          {
            id: "0",
            type: "error",
            content: errorMessage(error),
            timestamp: new Date(),
          },
        ]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSend = async (text?: string) => {
    const messageText = (text || inputValue).trim();
    if (!messageText || isTyping) return;

    const userMessage: Message = {
      id: `u-${Date.now()}`,
      type: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsTyping(true);

    try {
      const response: AskResponse = await ask(messageText);
      setOnline(true);
      setMessages((prev) => [
        ...prev,
        {
          id: `b-${Date.now()}`,
          type: "bot",
          content: response.answer,
          timestamp: new Date(),
          suggestions: response.suggestions,
          organizations: response.organizations,
          documents: response.documents,
          queryId: response.query_id,
          feedback: null,
          answered: response.answered,
        },
      ]);
    } catch (error) {
      // Aucune reponse de secours inventee cote front : le chatbot ne repond
      // que ce que le serveur a valide (regle de fiabilite du back-end).
      setOnline(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          type: "error",
          content: errorMessage(error),
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleFeedback = async (messageId: string, queryId: number, helpful: boolean) => {
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback: helpful } : m)));
    try {
      await sendFeedback(queryId, helpful);
    } catch {
      setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback: null } : m)));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200">
      {/* Chat Header */}
      <div className="bg-[rgb(4,108,180)] text-white px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
            <Bot className="text-[rgb(4,108,180)]" size={24} />
          </div>
          <div>
            <h2 className="font-semibold">{botName}</h2>
            <p className="text-sm text-white/90">
              {online === null ? "Connexion..." : online ? "En ligne" : "Service indisponible"}
            </p>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div className="h-[500px] overflow-y-auto p-6 space-y-4 bg-slate-50">
        {messages.map((message) => (
          <div key={message.id}>
            <div
              className={`flex gap-3 ${
                message.type === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {message.type !== "user" && (
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.type === "error" ? "bg-red-100" : "bg-[rgb(4,108,180)]"
                  }`}
                >
                  {message.type === "error" ? (
                    <AlertCircle className="text-red-600" size={18} />
                  ) : (
                    <Bot className="text-white" size={18} />
                  )}
                </div>
              )}

              <div
                className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                  message.type === "user"
                    ? "bg-[rgb(4,108,180)] text-white"
                    : message.type === "error"
                      ? "bg-red-50 border border-red-200 text-red-800"
                      : "bg-white border border-slate-200 text-slate-900"
                }`}
              >
                <p className="whitespace-pre-line">{message.content}</p>

                {/* Coordonnees des acteurs proposes : elles viennent de l'annuaire,
                    jamais du texte de la reponse (REQ-FUNC.2). */}
                {message.organizations && message.organizations.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {message.organizations.map((org) => (
                      <OrganizationCard key={org.id} organization={org} />
                    ))}
                  </div>
                )}

                {message.documents && message.documents.length > 0 && (
                  <p className="mt-3 text-xs text-slate-500">
                    Source : {message.documents[0].title}
                    {message.documents[0].section ? ` › ${message.documents[0].section}` : ""}
                  </p>
                )}

                <div className="flex items-center justify-between gap-3 mt-2">
                  <p
                    className={`text-xs ${
                      message.type === "user" ? "text-white/80" : "text-slate-500"
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString("fr-FR", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>

                  {/* Evaluation de la reponse (REQ-FUNC.3) : POST /feedback */}
                  {message.type === "bot" && typeof message.queryId === "number" && (
                    <div className="flex items-center gap-1">
                      {message.feedback === null ? (
                        <>
                          <button
                            aria-label="Cette réponse est utile"
                            onClick={() => handleFeedback(message.id, message.queryId as number, true)}
                            className="p-1 text-slate-400 hover:text-[rgb(4,108,180)] transition-colors"
                          >
                            <ThumbsUp size={14} />
                          </button>
                          <button
                            aria-label="Cette réponse n'est pas utile"
                            onClick={() => handleFeedback(message.id, message.queryId as number, false)}
                            className="p-1 text-slate-400 hover:text-red-600 transition-colors"
                          >
                            <ThumbsDown size={14} />
                          </button>
                        </>
                      ) : (
                        <span className="text-xs text-slate-400">Merci pour votre retour</span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {message.type === "user" && (
                <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center flex-shrink-0">
                  <User className="text-white" size={18} />
                </div>
              )}
            </div>

            {/* Suggestions */}
            {message.type === "bot" && message.suggestions && message.suggestions.length > 0 && (
              <div className="ml-11 mt-2 flex flex-wrap gap-2">
                {message.suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(suggestion)}
                    className="px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 hover:border-[rgb(4,108,180)] transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {isTyping && (
          <div className="flex gap-3">
            <div className="w-8 h-8 bg-[rgb(4,108,180)] rounded-full flex items-center justify-center">
              <Bot className="text-white" size={18} />
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-slate-200 p-4 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Posez votre question..."
            className="flex-1 px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)] focus:border-transparent"
          />
          <button
            onClick={() => handleSend()}
            disabled={!inputValue.trim() || isTyping}
            className="px-6 py-3 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

function OrganizationCard({ organization }: { organization: OrganizationResult }) {
  const site = organization.sites[0];
  const contact = organization.contacts[0];
  const website = organization.website.replace(/^https?:\/\//, "");

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
      <p className="font-medium text-slate-900">{organization.name}</p>
      <div className="mt-1 space-y-1 text-xs text-slate-600">
        {site && (site.address || site.city) && (
          <p className="flex items-center gap-2">
            <MapPin size={12} className="text-slate-400 flex-shrink-0" />
            <span>
              {[site.address, [site.postal_code, site.city].filter(Boolean).join(" ")]
                .filter(Boolean)
                .join(", ")}
            </span>
          </p>
        )}
        {contact && contact.phone && (
          <p className="flex items-center gap-2">
            <Phone size={12} className="text-slate-400 flex-shrink-0" />
            <span>{contact.phone}</span>
          </p>
        )}
        {contact && contact.email && (
          <p className="flex items-center gap-2">
            <Mail size={12} className="text-slate-400 flex-shrink-0" />
            <span>{contact.email}</span>
          </p>
        )}
        {organization.website && (
          <p className="flex items-center gap-2">
            <Globe size={12} className="text-slate-400 flex-shrink-0" />
            <a
              href={organization.website.startsWith("http") ? organization.website : `https://${website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[rgb(4,108,180)] hover:underline"
            >
              {website}
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
