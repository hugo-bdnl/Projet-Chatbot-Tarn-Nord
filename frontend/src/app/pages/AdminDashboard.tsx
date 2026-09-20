import { useEffect, useState } from "react";
import { Header } from "../components/Header";
import { OrganizationManager } from "../components/admin/OrganizationManager";
import { AnalyticsDashboard } from "../components/admin/AnalyticsDashboard";
import { ConfigurationPanel } from "../components/admin/ConfigurationPanel";
import { Building2, BarChart3, Settings, KeyRound } from "lucide-react";
import { API_BASE_URL, getAdminKey, getHealth, setAdminKey, type Health } from "../lib/api";

type TabType = "organizations" | "analytics" | "config";

export function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>("organizations");
  const [health, setHealth] = useState<Health | null>(null);
  const [apiKey, setApiKeyValue] = useState(getAdminKey());
  // Change a chaque enregistrement de cle : force le remontage des onglets
  // pour qu'ils rejouent leurs appels avec le nouvel en-tete.
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, [reloadToken]);

  const handleSaveKey = () => {
    setAdminKey(apiKey.trim());
    setReloadToken((value) => value + 1);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            Tableau de bord administrateur
          </h1>
          <p className="text-slate-600">
            Gérez l'annuaire, consultez les statistiques et configurez le chatbot
          </p>
        </div>

        {/* Etat du service et cle d'administration */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-sm">
            {health ? (
              <p className="text-slate-600">
                <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-2" />
                Connecté à {API_BASE_URL} — {health.organizations} organisations, {health.passages} passages
                indexés, modèle {health.model}
              </p>
            ) : (
              <p className="text-red-600">
                <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-2" />
                Service injoignable ({API_BASE_URL})
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <KeyRound size={18} className="text-slate-400" />
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKeyValue(e.target.value)}
              placeholder="Clé d'administration"
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
            <button
              onClick={handleSaveKey}
              className="px-4 py-2 text-sm bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] transition-colors"
            >
              Appliquer
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 border-b border-slate-200">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab("organizations")}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === "organizations"
                  ? "border-[rgb(4,108,180)] text-[rgb(4,108,180)]"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              <Building2 size={20} />
              Annuaire
            </button>
            <button
              onClick={() => setActiveTab("analytics")}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === "analytics"
                  ? "border-[rgb(4,108,180)] text-[rgb(4,108,180)]"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              <BarChart3 size={20} />
              Analytiques
            </button>
            <button
              onClick={() => setActiveTab("config")}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === "config"
                  ? "border-[rgb(4,108,180)] text-[rgb(4,108,180)]"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              <Settings size={20} />
              Configuration
            </button>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === "organizations" && <OrganizationManager key={`orgs-${reloadToken}`} />}
        {activeTab === "analytics" && <AnalyticsDashboard key={`analytics-${reloadToken}`} />}
        {activeTab === "config" && <ConfigurationPanel key={`config-${reloadToken}`} />}
      </main>
    </div>
  );
}
