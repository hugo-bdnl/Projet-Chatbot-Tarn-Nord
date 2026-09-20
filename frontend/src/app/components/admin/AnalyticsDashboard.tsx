import { useCallback, useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell,
} from "recharts";
import { MessageSquare, TrendingUp, Users, Clock, RefreshCw, AlertCircle } from "lucide-react";
import { getAnalytics, errorMessage, type AnalyticsSummary, type PeriodTotals } from "../../lib/api";

const PERIODS = [
  { days: 7, label: "7 jours" },
  { days: 30, label: "30 jours" },
  { days: 90, label: "90 jours" },
];

const PIE_COLORS = [
  "rgb(4, 108, 180)",
  "rgb(4, 172, 228)",
  "rgb(244, 148, 4)",
  "rgb(4, 124, 84)",
  "rgb(148, 108, 180)",
  "rgb(180, 84, 84)",
];

/** Variation entre la periode courante et la precedente, en points de pourcentage relatifs. */
function variation(current: number | null, previous: number | null): number | null {
  if (current === null || previous === null || previous === 0) return null;
  return Math.round(((current - previous) / previous) * 100);
}

function formatDay(iso: string): string {
  const [, month, day] = iso.split("-");
  return month && day ? `${day}/${month}` : iso;
}

export function AnalyticsDashboard() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    getAnalytics(days)
      .then((summary) => {
        setData(summary);
        setError(null);
      })
      .catch((err) => {
        setData(null);
        setError(errorMessage(err));
      })
      .finally(() => setLoading(false));
  }, [days]);

  useEffect(load, [load]);

  if (loading && !data) {
    return <p className="text-slate-600">Chargement des statistiques...</p>;
  }

  if (error) {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
        <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">Statistiques indisponibles</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { totals, previous } = data;
  const satisfaction = totals.satisfaction_rate === null ? null : Math.round(totals.satisfaction_rate * 100);
  const previousSatisfaction =
    previous.satisfaction_rate === null ? null : Math.round(previous.satisfaction_rate * 100);
  const latency = totals.avg_latency_ms === null ? null : totals.avg_latency_ms / 1000;
  const previousLatency = previous.avg_latency_ms === null ? null : previous.avg_latency_ms / 1000;

  const perDay = data.per_day.map((d) => ({ ...d, label: formatDay(d.date) }));
  const latencyByHour = data.latency_by_hour.map((h) => ({
    hour: `${h.hour}h`,
    time: Math.round(h.avg_latency_ms) / 1000,
  }));
  const empty = totals.conversations === 0;

  return (
    <div className="space-y-6">
      {/* Periode */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-600">
          Depuis le {data.since} — journal anonymise, purge automatique a 365 jours
        </p>
        <div className="flex items-center gap-2">
          {PERIODS.map((period) => (
            <button
              key={period.days}
              onClick={() => setDays(period.days)}
              className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                days === period.days
                  ? "border-[rgb(4,108,180)] bg-[rgb(4,108,180)]/10 text-[rgb(4,108,180)]"
                  : "border-slate-300 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {period.label}
            </button>
          ))}
          <button
            onClick={load}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Actualiser
          </button>
        </div>
      </div>

      {empty && (
        <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
          Aucune question posee sur la periode. Les statistiques se remplissent des les premieres
          conversations, et les questions restees sans reponse remontent ici pour enrichir l'annuaire.
        </p>
      )}

      {/* Stats Cards */}
      <div className="grid md:grid-cols-4 gap-4">
        <StatCard
          icon={<MessageSquare className="text-[rgb(4,108,180)]" size={20} />}
          iconBackground="bg-[rgb(4,108,180)]/10"
          value={String(totals.conversations)}
          label={`Conversations sur ${data.days} jours`}
          change={variation(totals.conversations, previous.conversations)}
        />
        <StatCard
          icon={<Users className="text-blue-600" size={20} />}
          iconBackground="bg-blue-100"
          value={String(totals.unique_sessions)}
          label="Utilisateurs uniques"
          change={variation(totals.unique_sessions, previous.unique_sessions)}
        />
        <StatCard
          icon={<TrendingUp className="text-green-600" size={20} />}
          iconBackground="bg-green-100"
          value={satisfaction === null ? "—" : `${satisfaction}%`}
          label={`Satisfaction (${totals.feedback_count} avis)`}
          change={variation(satisfaction, previousSatisfaction)}
        />
        <StatCard
          icon={<Clock className="text-orange-600" size={20} />}
          iconBackground="bg-orange-100"
          value={latency === null ? "—" : `${latency.toFixed(2)}s`}
          label="Temps de reponse moyen"
          change={variation(latency, previousLatency)}
          lowerIsBetter
        />
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Conversations par jour</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={perDay}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" stroke="#64748b" />
              <YAxis stroke="#64748b" allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" name="questions" fill="rgb(4, 108, 180)" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Sujets les plus demandes</h3>
          {data.categories.length === 0 ? (
            <p className="text-sm text-slate-500">Aucune categorie detectee sur la periode.</p>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={data.categories}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} (${Math.round((percent ?? 0) * 100)}%)`}
                  outerRadius={80}
                  dataKey="count"
                  nameKey="name"
                >
                  {data.categories.map((entry, index) => (
                    <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6 md:col-span-2">
          <h3 className="font-semibold text-slate-900 mb-4">Temps de reponse moyen par heure (secondes)</h3>
          {latencyByHour.length === 0 ? (
            <p className="text-sm text-slate-500">Pas encore de mesure sur la periode.</p>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={latencyByHour}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="hour" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip />
                <Line type="monotone" dataKey="time" name="secondes" stroke="rgb(4, 108, 180)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Questions */}
      <div className="grid md:grid-cols-2 gap-6">
        <QuestionList
          title="Questions frequentes"
          items={data.top_questions}
          emptyLabel="Aucune question sur la periode."
        />
        <QuestionList
          title="Questions restees sans reponse"
          items={data.unanswered_questions}
          emptyLabel="Aucune question sans reponse : l'annuaire couvre les demandes recues."
          hint="A exploiter pour enrichir l'annuaire : ce sont les besoins que le chatbot n'a pas su orienter."
          accent="border-orange-200"
        />
      </div>

      {data.top_organizations.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Acteurs les plus proposes</h3>
          <div className="flex flex-wrap gap-2">
            {data.top_organizations.map((org) => (
              <span
                key={org.name}
                className="px-3 py-1 bg-[rgb(4,108,180)]/10 text-[rgb(4,108,180)] rounded-full text-sm"
              >
                {org.name} · {org.count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon, iconBackground, value, label, change, lowerIsBetter,
}: {
  icon: React.ReactNode;
  iconBackground: string;
  value: string;
  label: string;
  change: number | null;
  lowerIsBetter?: boolean;
}) {
  const good = change === null ? null : lowerIsBetter ? change <= 0 : change >= 0;
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-2">
        <div className={`w-10 h-10 ${iconBackground} rounded-lg flex items-center justify-center`}>{icon}</div>
        {change !== null && (
          <span className={`text-sm font-medium ${good ? "text-green-600" : "text-red-600"}`}>
            {change > 0 ? "+" : ""}
            {change}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-sm text-slate-600">{label}</p>
    </div>
  );
}

function QuestionList({
  title, items, emptyLabel, hint, accent,
}: {
  title: string;
  items: Array<{ question: string; count: number }>;
  emptyLabel: string;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className={`bg-white rounded-lg border p-6 ${accent ?? "border-slate-200"}`}>
      <h3 className="font-semibold text-slate-900 mb-1">{title}</h3>
      {hint && <p className="text-sm text-slate-500 mb-4">{hint}</p>}
      {items.length === 0 ? (
        <p className="text-sm text-slate-500 mt-3">{emptyLabel}</p>
      ) : (
        <div className="space-y-3 mt-3">
          {items.map((item, idx) => (
            <div
              key={`${item.question}-${idx}`}
              className="flex items-center justify-between gap-4 py-2 border-b border-slate-100 last:border-0"
            >
              <p className="text-slate-700">{item.question}</p>
              <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm font-medium flex-shrink-0">
                {item.count}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
