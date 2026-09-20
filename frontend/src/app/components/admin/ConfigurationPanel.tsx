import { useEffect, useState } from "react";
import { Save, RefreshCw, AlertCircle, Check } from "lucide-react";
import {
  getAdminConfig, saveAdminConfig, resetAdminConfig, errorMessage,
  type ChatbotConfig, type Category,
} from "../../lib/api";

const inputClass =
  "w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]";

export function ConfigurationPanel() {
  const [config, setConfig] = useState<ChatbotConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getAdminConfig()
      .then((loaded) => {
        setConfig(loaded);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  const update = (patch: Partial<ChatbotConfig>) => {
    setConfig((prev) => (prev ? { ...prev, ...patch } : prev));
    setSaved(false);
  };

  const updateCategory = (index: number, patch: Partial<Category>) => {
    setConfig((prev) => {
      if (!prev) return prev;
      const categories = [...prev.categories];
      categories[index] = { ...categories[index], ...patch };
      return { ...prev, categories };
    });
    setSaved(false);
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      setConfig(await saveAdminConfig(config));
      setSaved(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    setError(null);
    try {
      setConfig(await resetAdminConfig());
      setSaved(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-slate-600">Chargement de la configuration...</p>;

  if (error && !config) {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
        <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">Configuration indisponible</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="space-y-6">
      {/* General Settings */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Parametres generaux</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Nom du chatbot</label>
            <input
              type="text"
              value={config.name}
              onChange={(e) => update({ name: e.target.value })}
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Message d'accueil</label>
            <textarea
              rows={3}
              value={config.welcome_message}
              onChange={(e) => update({ welcome_message: e.target.value })}
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Suggestions affichees a l'ouverture
            </label>
            <textarea
              rows={4}
              value={config.initial_suggestions.join("\n")}
              onChange={(e) =>
                update({ initial_suggestions: e.target.value.split("\n").map((v) => v.trim()).filter(Boolean) })
              }
              className={inputClass}
            />
            <p className="text-xs text-slate-500 mt-1">Une suggestion par ligne, huit au maximum.</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Acteurs proposes au maximum par reponse
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={config.max_organizations}
              onChange={(e) => update({ max_organizations: Number(e.target.value) })}
              className={inputClass}
            />
          </div>
        </div>
      </div>

      {/* Response Configuration */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Configuration des reponses</h3>
        <div className="space-y-4">
          <Toggle
            title="Suggestions automatiques"
            description="Afficher des suggestions de questions"
            checked={config.suggestions_enabled}
            onChange={(checked) => update({ suggestions_enabled: checked })}
          />
          <Toggle
            title="Orientation automatique"
            description="Orienter vers les acteurs de l'annuaire (sinon : extraits documentaires seulement)"
            checked={config.orientation_enabled}
            onChange={(checked) => update({ orientation_enabled: checked })}
          />
          <Toggle
            title="Collecte des statistiques"
            description="Journaliser les questions, anonymisees et purgees automatiquement (REQ-FUNC.4)"
            checked={config.analytics_enabled}
            onChange={(checked) => update({ analytics_enabled: checked })}
          />

          <div className="grid md:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Phrase d'introduction de l'orientation
              </label>
              <textarea
                rows={2}
                value={config.orientation_intro}
                onChange={(e) => update({ orientation_intro: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Phrase de relance</label>
              <textarea
                rows={2}
                value={config.orientation_outro}
                onChange={(e) => update({ orientation_outro: e.target.value })}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Message quand rien n'est assez fiable
            </label>
            <textarea
              rows={3}
              value={config.no_answer_message}
              onChange={(e) => update({ no_answer_message: e.target.value })}
              className={inputClass}
            />
            <p className="text-xs text-slate-500 mt-1">
              Les categories ci-dessous sont ajoutees a la suite de ce message pour aider a reformuler.
            </p>
          </div>
        </div>
      </div>

      {/* Categories */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Categories de besoins</h3>
        <p className="text-sm text-slate-600 mb-4">
          Les mots-cles servent a classer les questions dans les analytiques ; la question d'exemple est
          proposee a l'usager quand le chatbot ne trouve pas de reponse fiable.
        </p>

        <div className="space-y-4">
          {config.categories.map((category, index) => (
            <div key={index} className="rounded-lg border border-slate-200 p-4 space-y-3">
              <input
                type="text"
                value={category.name}
                onChange={(e) => updateCategory(index, { name: e.target.value })}
                className={`${inputClass} font-medium`}
              />
              <div>
                <label className="block text-xs text-slate-500 mb-1">Mots-cles (separes par des virgules)</label>
                <input
                  type="text"
                  value={category.keywords.join(", ")}
                  onChange={(e) =>
                    updateCategory(index, {
                      keywords: e.target.value.split(",").map((v) => v.trim()).filter(Boolean),
                    })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Question d'exemple</label>
                <input
                  type="text"
                  value={category.example_question}
                  onChange={(e) => updateCategory(index, { example_question: e.target.value })}
                  className={inputClass}
                />
              </div>
            </div>
          ))}
          {config.categories.length === 0 && (
            <p className="text-sm text-slate-500">Aucune categorie configuree.</p>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end items-center gap-3">
        {saved && (
          <span className="flex items-center gap-2 text-sm text-green-600">
            <Check size={16} />
            Configuration enregistree
          </span>
        )}
        <button
          onClick={handleReset}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={20} />
          Reinitialiser
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] disabled:bg-slate-300 transition-colors"
        >
          <Save size={20} />
          {saving ? "Enregistrement..." : "Enregistrer les modifications"}
        </button>
      </div>
    </div>
  );
}

function Toggle({
  title, description, checked, onChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium text-slate-900">{title}</p>
        <p className="text-sm text-slate-600">{description}</p>
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />
        <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[rgb(4,108,180)]/20 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[rgb(4,108,180)]"></div>
      </label>
    </div>
  );
}
