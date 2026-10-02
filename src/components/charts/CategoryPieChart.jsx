import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const COLORS = ['#7C3AED', '#14B8A6', '#F97316', '#38BDF8', '#EAB308', '#F43F5E', '#22C55E', '#64748B'];

export default function CategoryPieChart({ data }) {
  return (
    <div className="h-80 rounded-3xl border border-slate-800/80 bg-slate-950/80 p-4">
      <h2 className="mb-4 text-lg font-semibold text-slate-100">Spending Breakdown</h2>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="amount" nameKey="category" cx="50%" cy="50%" outerRadius={90} innerRadius={40} paddingAngle={3}>
            {data.map((entry, index) => (
              <Cell key={`cell-${entry.category}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `₹${value.toLocaleString('en-IN')}`} />
          <Legend verticalAlign="bottom" height={36} formatter={(value) => <span className="text-slate-200">{value}</span>} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
