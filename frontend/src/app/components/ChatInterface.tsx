import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";

interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  timestamp: Date;
  suggestions?: string[];
}

const initialMessage: Message = {
  id: "0",
  type: "bot",
  content: "Bonjour ! Je suis le chatbot du Grand Albigeois. Comment puis-je vous aider aujourd'hui ? Je peux vous orienter vers les acteurs de l'innovation du territoire pour vos projets.",
  timestamp: new Date(),
  suggestions: [
    "J'ai besoin d'une pièce métallique spécifique",
    "Je cherche des aides pour innover",
    "Je recherche des solutions RH",
    "J'ai un projet de transition énergétique"
  ]
};

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getBotResponse = (userMessage: string): { content: string; suggestions?: string[] } => {
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes("pièce") || lowerMessage.includes("métallique") || lowerMessage.includes("fournisseur")) {
      return {
        content: "Je comprends que vous recherchez un fournisseur de pièces métalliques. Je peux vous orienter vers plusieurs acteurs spécialisés :\n\n• **IMT Mines Albi** - Laboratoire de métallurgie et procédés\n• **Centre Technique ICA** - Spécialiste en fabrication additive métallique\n• **Plateforme CRITT** - Expertise en usinage de précision\n\nSouhaitez-vous plus d'informations sur l'un de ces acteurs ?",
        suggestions: ["En savoir plus sur IMT Mines Albi", "Contacter le Centre ICA", "Voir d'autres acteurs"]
      };
    } else if (lowerMessage.includes("aide") || lowerMessage.includes("innov") || lowerMessage.includes("financement")) {
      return {
        content: "Pour vos besoins en innovation et financement, plusieurs organismes peuvent vous accompagner :\n\n• **AD'OCC** - Aides régionales et accompagnement des entreprises\n• **BPI France** - Prêts et subventions pour l'innovation\n• **CNAM Formation** - Formation et développement des compétences\n\nDe quel type d'aide avez-vous besoin ?",
        suggestions: ["Financement de projets", "Accompagnement stratégique", "Formation des équipes"]
      };
    } else if (lowerMessage.includes("rh") || lowerMessage.includes("recrutement") || lowerMessage.includes("formation")) {
      return {
        content: "Pour vos besoins en ressources humaines, voici les structures qui peuvent vous accompagner :\n\n• **Pôle Emploi Albi** - Recrutement et sourcing\n• **CNAM Formation Continue** - Formation professionnelle\n• **Mission Locale** - Recrutement de jeunes talents\n• **OPCO** - Financement des formations\n\nQuel est votre besoin prioritaire ?",
        suggestions: ["Recruter du personnel", "Former mes équipes", "Mobilité des salariés"]
      };
    } else if (lowerMessage.includes("énergie") || lowerMessage.includes("énergétique") || lowerMessage.includes("environnement")) {
      return {
        content: "Pour vos projets de transition énergétique, plusieurs acteurs peuvent vous conseiller :\n\n• **Centre RAPSODEE** - Recherche sur l'énergie et l'environnement\n• **ADEME Occitanie** - Aides à la transition écologique\n• **CCI Tarn** - Diagnostic énergétique entreprise\n\nAvez-vous déjà un projet défini ?",
        suggestions: ["Réduire ma consommation", "Énergies renouvelables", "Diagnostic énergétique"]
      };
    } else if (lowerMessage.includes("merci") || lowerMessage.includes("parfait")) {
      return {
        content: "Avec plaisir ! N'hésitez pas si vous avez d'autres questions. Je suis là pour vous aider à trouver les bons interlocuteurs.",
        suggestions: ["Poser une autre question", "Voir tous les acteurs"]
      };
    } else {
      return {
        content: "Je peux vous aider à trouver les bons interlocuteurs pour vos projets. Pouvez-vous préciser votre besoin ?\n\nJe peux vous orienter vers :\n• Des laboratoires de recherche\n• Des plateformes techniques\n• Des centres de formation\n• Des organismes de financement",
        suggestions: [
          "Recherche et innovation",
          "Formation et RH",
          "Transition énergétique",
          "Financement"
        ]
      };
    }
  };

  const handleSend = (text?: string) => {
    const messageText = text || inputValue.trim();
    if (!messageText) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsTyping(true);

    // Simulate bot response
    setTimeout(() => {
      const response = getBotResponse(messageText);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: response.content,
        timestamp: new Date(),
        suggestions: response.suggestions,
      };

      setMessages((prev) => [...prev, botMessage]);
      setIsTyping(false);
    }, 1000);
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
            <h2 className="font-semibold">Assistant Grand Albigeois</h2>
            <p className="text-sm text-white/90">En ligne</p>
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
              {message.type === "bot" && (
                <div className="w-8 h-8 bg-[rgb(4,108,180)] rounded-full flex items-center justify-center flex-shrink-0">
                  <Bot className="text-white" size={18} />
                </div>
              )}
              
              <div
                className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                  message.type === "user"
                    ? "bg-[rgb(4,108,180)] text-white"
                    : "bg-white border border-slate-200 text-slate-900"
                }`}
              >
                <p className="whitespace-pre-line">{message.content}</p>
                <p
                  className={`text-xs mt-2 ${
                    message.type === "user" ? "text-white/80" : "text-slate-500"
                  }`}
                >
                  {message.timestamp.toLocaleTimeString("fr-FR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>

              {message.type === "user" && (
                <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center flex-shrink-0">
                  <User className="text-white" size={18} />
                </div>
              )}
            </div>

            {/* Suggestions */}
            {message.type === "bot" && message.suggestions && (
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
            disabled={!inputValue.trim()}
            className="px-6 py-3 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}