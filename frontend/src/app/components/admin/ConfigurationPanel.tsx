import { Save, RefreshCw } from "lucide-react";

export function ConfigurationPanel() {
  return (
    <div className="space-y-6">
      {/* General Settings */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Paramètres généraux</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Nom du chatbot
            </label>
            <input
              type="text"
              defaultValue="Assistant Grand Albigeois"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Message d'accueil
            </label>
            <textarea
              rows={3}
              defaultValue="Bonjour ! Je suis le chatbot du Grand Albigeois. Comment puis-je vous aider aujourd'hui ?"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Temps de réponse simulé (ms)
            </label>
            <input
              type="number"
              defaultValue="1000"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
          </div>
        </div>
      </div>

      {/* Response Configuration */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Configuration des réponses</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Suggestions automatiques</p>
              <p className="text-sm text-slate-600">Afficher des suggestions de questions</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" defaultChecked className="sr-only peer" />
              <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[rgb(4,108,180)]/20 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[rgb(4,108,180)]"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Orientation automatique</p>
              <p className="text-sm text-slate-600">Orienter vers les acteurs pertinents</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" defaultChecked className="sr-only peer" />
              <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[rgb(4,108,180)]/20 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[rgb(4,108,180)]"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Collecte des statistiques</p>
              <p className="text-sm text-slate-600">Enregistrer les conversations anonymisées</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" defaultChecked className="sr-only peer" />
              <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[rgb(4,108,180)]/20 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[rgb(4,108,180)]"></div>
            </label>
          </div>
        </div>
      </div>

      {/* Keywords Management */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Gestion des mots-clés</h3>
        <p className="text-sm text-slate-600 mb-4">
          Configurez les mots-clés utilisés pour détecter les besoins des utilisateurs
        </p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Innovation & Financement
            </label>
            <input
              type="text"
              defaultValue="aide, innovation, financement, subvention, accompagnement"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Formation & RH
            </label>
            <input
              type="text"
              defaultValue="rh, recrutement, formation, compétences, mobilité"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Recherche technique
            </label>
            <input
              type="text"
              defaultValue="pièce, métallique, fournisseur, fabrication, technique"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Transition énergétique
            </label>
            <input
              type="text"
              defaultValue="énergie, énergétique, environnement, transition, écologique"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
            />
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-3">
        <button className="flex items-center gap-2 px-6 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors">
          <RefreshCw size={20} />
          Réinitialiser
        </button>
        <button className="flex items-center gap-2 px-6 py-3 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] transition-colors">
          <Save size={20} />
          Enregistrer les modifications
        </button>
      </div>
    </div>
  );
}