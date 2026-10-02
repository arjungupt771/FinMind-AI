import useAppStore from '../context/useAppStore';
import CashflowChart from '../components/charts/CashflowChart';
import CategoryPieChart from '../components/charts/CategoryPieChart';

const KPI_CARD = ({ label, value, accent }) => (
  <div className="kpi-card grid gap-2 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-5">
    <div className="text-sm text-slate-400">{label}</div>
    <div className={`text-2xl font-semibold ${accent}`}>{value}</div>
  </div>
);

export default function DashboardPage() {
  const transactions = useAppStore((state) => state.transactions);
  const overview = useAppStore((state) => state.calculateOverview());
  const health = useAppStore((state) => state.calculateHealth());
  const subscriptions = useAppStore((state) => state.calculateSubscriptions());

  return (
    <section className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <KPI_CARD label="Total Balance" value={`₹${overview.balance.toLocaleString('en-IN')}`} accent="text-white" />
        <KPI_CARD label="Monthly Income" value={`₹${overview.income.toLocaleString('en-IN')}`} accent="text-emerald-300" />
        <KPI_CARD label="Monthly Expenses" value={`₹${overview.expense.toLocaleString('en-IN')}`} accent="text-fuchsia-300" />
        <KPI_CARD label="Savings Rate" value={`${overview.savingsRate.toFixed(1)}%`} accent="text-cyan-300" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.86fr]">
        <CashflowChart data={overview.monthlyCashflow} />
        <CategoryPieChart data={overview.spendingBreakdown} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_0.72fr]">
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold text-slate-100">Financial Health</h2>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-6">
              <div className="text-sm uppercase tracking-[0.2em] text-slate-500">Health score</div>
              <div className="mt-4 text-5xl font-semibold text-white">{health.score}</div>
              <div className="mt-2 text-sm text-slate-400">{health.score >= 80 ? 'Excellent' : health.score >= 60 ? 'Good' : 'Needs improvement'}</div>
            </div>
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-6">
              <div className="mb-3 text-sm uppercase tracking-[0.2em] text-slate-500">Quick insights</div>
              <ul className="space-y-2 text-slate-300">
                {health.explanations.map((line) => (<li key={line} className="rounded-2xl bg-slate-900/80 p-3">{line}</li>))}
              </ul>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="mb-4 text-xl font-semibold text-slate-100">Subscription Snapshot</h2>
          <div className="space-y-3">
            {subscriptions.length ? (
              subscriptions.slice(0, 4).map((item) => (
                <div key={item.merchant} className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-4">
                  <div className="flex items-center justify-between gap-4 text-slate-100">
                    <span>{item.merchant}</span>
                    <span className="text-sm text-slate-400">₹{item.monthlyAmount.toLocaleString('en-IN')}/mo</span>
                  </div>
                  <div className="mt-2 text-sm text-slate-500">Est. annual cost ₹{item.annualEstimate.toLocaleString('en-IN')}</div>
                </div>
              ))
            ) : (
              <div className="rounded-3xl border border-dashed border-slate-700/70 bg-slate-900/70 p-6 text-slate-500">Upload statements to detect recurring subscriptions and savings opportunities.</div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
