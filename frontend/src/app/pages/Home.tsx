import { ChatInterface } from "../components/ChatInterface";
import { Header } from "../components/Header";

export function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-slate-900 mb-4">
              Chatbot Grand Albigeois
            </h1>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Connectez-vous facilement avec les acteurs de l'innovation du territoire. 
              Posez vos questions et trouvez les bons interlocuteurs pour vos projets.
            </p>
            <a 
              href="https://www.grand-albigeois.fr/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="inline-block mt-4 text-[rgb(4,108,180)] hover:underline"
            >
              www.grand-albigeois.fr
            </a>
          </div>
          <ChatInterface />
        </div>
      </main>
    </div>
  );
}