import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from "recharts";
import { MessageSquare, TrendingUp, Users, Clock } from "lucide-react";

const conversationsData = [
  { date: "Lun", count: 45 },
  { date: "Mar", count: 52 },
  { date: "Mer", count: 61 },
  { date: "Jeu", count: 48 },
  { date: "Ven", count: 70 },
  { date: "Sam", count: 28 },
  { date: "Dim", count: 20 },
];

const topicsData = [
  { name: "Innovation & Financement", value: 35, color: "rgb(4, 108, 180)" },
  { name: "Formation & RH", value: 28, color: "rgb(4, 172, 228)" },
  { name: "Recherche technique", value: 22, color: "rgb(244, 148, 4)" },
  { name: "Transition énergétique", value: 15, color: "rgb(4, 124, 84)" },
];

const responseTimeData = [
  { hour: "9h", time: 1.2 },
  { hour: "11h", time: 1.5 },
  { hour: "13h", time: 2.1 },
  { hour: "15h", time: 1.8 },
  { hour: "17h", time: 1.4 },
];

export function AnalyticsDashboard() {
  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="w-10 h-10 bg-[rgb(4,108,180)]/10 rounded-lg flex items-center justify-center">
              <MessageSquare className="text-[rgb(4,108,180)]" size={20} />
            </div>
            <span className="text-green-600 text-sm font-medium">+12%</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">324</p>
          <p className="text-sm text-slate-600">Conversations cette semaine</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Users className="text-blue-600" size={20} />
            </div>
            <span className="text-green-600 text-sm font-medium">+8%</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">156</p>
          <p className="text-sm text-slate-600">Utilisateurs uniques</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="text-green-600" size={20} />
            </div>
            <span className="text-green-600 text-sm font-medium">+15%</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">89%</p>
          <p className="text-sm text-slate-600">Taux de satisfaction</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <Clock className="text-orange-600" size={20} />
            </div>
            <span className="text-red-600 text-sm font-medium">-5%</span>
          </div>
          <p className="text-2xl font-bold text-slate-900">1.6s</p>
          <p className="text-sm text-slate-600">Temps de réponse moyen</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Conversations par jour */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Conversations par jour</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={conversationsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip />
              <Bar dataKey="count" fill="rgb(4, 108, 180)" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Sujets les plus demandés */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-900 mb-4">Sujets les plus demandés</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={topicsData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {topicsData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Temps de réponse */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 md:col-span-2">
          <h3 className="font-semibold text-slate-900 mb-4">Temps de réponse moyen (secondes)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={responseTimeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="hour" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip />
              <Line type="monotone" dataKey="time" stroke="rgb(4, 108, 180)" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Questions */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Questions fréquentes</h3>
        <div className="space-y-3">
          {[
            { question: "Comment trouver un fournisseur de pièces métalliques ?", count: 47 },
            { question: "Quelles aides financières pour l'innovation ?", count: 38 },
            { question: "Comment former mes équipes ?", count: 32 },
            { question: "Accompagnement transition énergétique ?", count: 28 },
            { question: "Contacts pour projets de recherche ?", count: 24 },
          ].map((item, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
              <p className="text-slate-700">{item.question}</p>
              <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm font-medium">
                {item.count}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}