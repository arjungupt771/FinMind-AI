import { useState } from 'react';
import useAppStore from '../context/useAppStore';

const presetGoals = ['Emergency Fund', 'Laptop', 'Vehicle', 'Travel', 'House'];

export default function GoalsPage() {
  const [form, setForm] = useState({ name: '', target: '', current: '', monthlyContribution: '' });
  const goals = useAppStore((state) => state.calculateGoals());
  const createGoal = useAppStore((state) => state.createGoal);
  const removeGoal = useAppStore((state) => state.removeGoal);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!form.name || !Number(form.target)) return;
    createGoal({
      name: form.name,
      target: Number(form.target),
      current: Number(form.current || 0),
      monthlyContribution: Number(form.monthlyContribution || 0),
    });
    setForm({ name: '', target: '', current: '', monthlyContribution: '' });
  };

  return (
    <section className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-[0.68fr_0.92fr]">
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold text-slate-100">Create a financial goal</h2>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <select
              className="w-full rounded-3xl border border-slate-800/80 bg-slate-950/80 px-4 py-3 text-slate-100"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            >
              <option value="">Choose goal type</option>
              {presetGoals.map((goal) => (<option key={goal} value={goal}>{goal}</option>))}
            </select>
            <input
              className="w-full rounded-3xl border border-slate-800/80 bg-slate-950/80 px-4 py-3 text-slate-100"
              type="number"
              placeholder="Target amount"
              value={form.target}
              onChange={(e) => setForm({ ...form, target: e.target.value })}
            />
            <input
              className="w-full rounded-3xl border border-slate-800/80 bg-slate-950/80 px-4 py-3 text-slate-100"
              type="number"
              placeholder="Current saved"
              value={form.current}
              onChange={(e) => setForm({ ...form, current: e.target.value })}
            />
            <input
              className="w-full rounded-3xl border border-slate-800/80 bg-slate-950/80 px-4 py-3 text-slate-100"
              type="number"
              placeholder="Monthly contribution"
              value={form.monthlyContribution}
              onChange={(e) => setForm({ ...form, monthlyContribution: e.target.value })}
            />
            <button type="submit" className="w-full rounded-3xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-500">Create goal</button>
          </form>
        </div>
        <div className="card">
          <h2 className="mb-4 text-xl font-semibold text-slate-100">Goal progress</h2>
          <div className="space-y-4">
            {goals.length ? goals.map((goal) => (
              <div key={goal.id} className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold text-slate-100">{goal.name}</p>
                    <p className="text-sm text-slate-400">{goal.progress}% complete</p>
                  </div>
                  <button type="button" onClick={() => removeGoal(goal.id)} className="rounded-full border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800">Complete</button>
                </div>
                <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full bg-brand-600" style={{ width: `${goal.progress}%` }} />
                </div>
                <div className="mt-3 flex items-center justify-between text-sm text-slate-400">
                  <span>₹{goal.current.toLocaleString('en-IN')} saved</span>
                  <span>Target ₹{goal.target.toLocaleString('en-IN')}</span>
                </div>
                <div className="mt-3 text-sm text-slate-500">Monthly requirement: ₹{goal.monthlyRequirement.toLocaleString('en-IN')} · Due {goal.predictedCompletion}</div>
              </div>
            )) : <div className="rounded-3xl border border-dashed border-slate-700/70 bg-slate-900/70 p-6 text-center text-slate-500">Add a goal to begin tracking savings progress.</div>}
          </div>
        </div>
      </div>
    </section>
  );
}
