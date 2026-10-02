import { Bar, ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, CartesianGrid, BarChart } from 'recharts';

export default function CashflowChart({ data }) {
  return (
    <div className="h-80 rounded-3xl border border-slate-800/80 bg-slate-950/80 p-4">
      <h2 className="mb-4 text-lg font-semibold text-slate-100">Monthly Cash Flow</h2>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: '#94A3B8' }} />
          <YAxis tick={{ fill: '#94A3B8' }} />
          <Tooltip formatter={(value) => `₹${value.toLocaleString('en-IN')}`} />
          <Legend formatter={(value) => <span className="text-slate-200">{value}</span>} />
          <Bar dataKey="income" fill="#14B8A6" radius={[12, 12, 0, 0]} />
          <Bar dataKey="expense" fill="#8B5CF6" radius={[12, 12, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
