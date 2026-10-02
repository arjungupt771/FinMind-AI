import { useMemo, useState } from 'react';
import useAppStore from '../context/useAppStore';

const CATEGORY_OPTIONS = ['All', 'Food', 'Travel', 'Shopping', 'Bills', 'Entertainment', 'Investments', 'Health', 'Miscellaneous', 'Income'];

export default function TransactionsPage() {
  const [filter, setFilter] = useState('All');
  const transactions = useAppStore((state) => state.transactions);
  const addTransactions = useAppStore((state) => state.addTransactions);
  const uploads = useAppStore((state) => state.uploads);

  const filtered = useMemo(() => {
    if (filter === 'All') return transactions;
    return transactions.filter((tx) => tx.category === filter);
  }, [filter, transactions]);

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await addTransactions(file);
  };

  return (
    <section className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold text-slate-100">Transaction history</h2>
          <div className="mb-4 flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((category) => (
              <button
                key={category}
                type="button"
                onClick={() => setFilter(category)}
                className={`rounded-full border px-4 py-2 text-sm ${filter === category ? 'border-brand-500 bg-brand-600/20 text-white' : 'border-slate-700 text-slate-300 hover:bg-slate-800'}`}
              >
                {category}
              </button>
            ))}
          </div>
          <div className="space-y-3">
            {filtered.length ? filtered.map((tx) => (
              <div key={tx.id} className="flex flex-col gap-2 rounded-3xl border border-slate-800/80 bg-slate-950/80 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-sm text-slate-400">{new Date(tx.date).toLocaleDateString()}</div>
                  <p className="font-semibold text-slate-100">{tx.description || tx.merchant}</p>
                  <div className="text-sm text-slate-500">{tx.category} · {tx.type}</div>
                </div>
                <div className={`text-lg font-semibold ${tx.amount >= 0 ? 'text-emerald-300' : 'text-fuchsia-300'}`}>
                  {tx.amount >= 0 ? '+' : '-'}₹{Math.abs(tx.amount).toLocaleString('en-IN')}
                </div>
              </div>
            )) : <div className="rounded-3xl border border-dashed border-slate-700/70 bg-slate-900/70 p-8 text-center text-slate-500">No transactions found for this filter.</div>}
          </div>
        </div>

        <div className="space-y-4">
          <div className="card">
            <h2 className="mb-4 text-xl font-semibold text-slate-100">Upload statement</h2>
            <p className="mb-4 text-sm text-slate-400">Drop a CSV, XLSX, or PDF bank statement to import transaction history and uncover spending insights.</p>
            <label className="block cursor-pointer rounded-3xl border border-dashed border-slate-700/80 bg-slate-950/80 p-6 text-center text-slate-300 transition hover:bg-slate-900">
              <input type="file" accept=".csv,.xlsx,.xls,.pdf" className="hidden" onChange={handleFileChange} />
              <div className="text-3xl">📥</div>
              <div className="mt-3 font-medium text-slate-100">Choose file or drop here</div>
            </label>
          </div>

          <div className="card">
            <h2 className="mb-4 text-xl font-semibold text-slate-100">Upload history</h2>
            <div className="space-y-3">
              {uploads.length ? uploads.map((upload) => (
                <div key={upload.id} className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-4">
                  <div className="flex items-center justify-between text-sm text-slate-300">
                    <span>{upload.fileName}</span>
                    <span>{new Date(upload.uploadedAt).toLocaleDateString()}</span>
                  </div>
                  <div className="mt-2 text-slate-400">{upload.transactionCount} transactions · {upload.status}</div>
                </div>
              )) : <div className="rounded-3xl border border-dashed border-slate-700/70 bg-slate-900/70 p-6 text-center text-slate-500">No files imported yet.</div>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
