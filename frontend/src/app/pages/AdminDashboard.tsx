import { useState } from "react";
import { Header } from "../components/Header";
import { OrganizationManager } from "../components/admin/OrganizationManager";
import { AnalyticsDashboard } from "../components/admin/AnalyticsDashboard";
import { ConfigurationPanel } from "../components/admin/ConfigurationPanel";
import { Building2, BarChart3, Settings } from "lucide-react";

type TabType = "organizations" | "analytics" | "config";

export function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>("organizations");

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
        {activeTab === "organizations" && <OrganizationManager />}
        {activeTab === "analytics" && <AnalyticsDashboard />}
        {activeTab === "config" && <ConfigurationPanel />}
      </main>
    </div>
  );
}