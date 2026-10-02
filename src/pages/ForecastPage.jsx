import useAppStore from '../context/useAppStore';

export default function ForecastPage() {
  const forecast = useAppStore((state) => state.calculateForecast(12));
  const health = useAppStore((state) => state.calculateHealth());
  const anomalies = useAppStore((state) => state.calculateAnomalies());

  return (
    <section className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold text-slate-100">12-month forecast</h2>
          <div className="overflow-hidden rounded-3xl border border-slate-800/80 bg-slate-950/80">
            <div className="grid grid-cols-3 gap-4 border-b border-slate-800/80 px-6 py-4 text-sm uppercase tracking-[0.15em] text-slate-500">
              <span>Month</span>
              <span>Expenses</span>
              <span>Savings</span>
            </div>
            <div className="divide-y divide-slate-800/70">
              {forecast.map((item) => (
                <div key={item.month} className="grid grid-cols-3 gap-4 px-6 py-4 text-slate-200">
                  <span>{item.month}</span>
                  <span>₹{item.expense.toLocaleString('en-IN')}</span>
                  <span>₹{item.savings.toLocaleString('en-IN')}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold text-slate-100">Forecast health</h2>
          <div className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-6">
            <div className="text-3xl font-semibold text-white">{health.score}</div>
            <p className="mt-3 text-slate-400">Projected health score based on upcoming expense and savings trends.</p>
            <div className="mt-6 space-y-3 text-sm text-slate-300">
              <p>Investment allocation: {health.investmentRatio.toFixed(1)}%</p>
              <p>Emergency coverage: {health.emergencyCoverage.toFixed(1)} months</p>
              <p>Expense ratio: {health.expenseRatio.toFixed(1)}%</p>
            </div>
          </div>
          <div className="mt-6 rounded-3xl border border-slate-800/80 bg-slate-950/80 p-6">
            <h3 className="mb-4 text-lg font-semibold text-slate-100">Anomalies</h3>
            {anomalies.oddTransactions.length ? (
              anomalies.oddTransactions.slice(0, 4).map((tx) => (
                <div key={tx.id || tx.date + tx.amount} className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-4 mb-3">
                  <div className="font-medium text-slate-100">{tx.merchant || tx.description}</div>
                  <div className="text-sm text-slate-400">₹{Math.abs(tx.amount).toLocaleString('en-IN')} · {new Date(tx.date).toLocaleDateString()}</div>
                </div>
              ))
            ) : (
              <p className="text-slate-500">No unusual expenses found in your recent history.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
