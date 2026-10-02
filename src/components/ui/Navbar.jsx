import { Link } from 'react-router-dom';

export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-brand-600/15 p-3 text-brand-300 shadow-lg shadow-brand-900/20">
            <span className="text-xl">💡</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-100">FinMind AI</h1>
            <p className="text-sm text-slate-500">AI-powered personal finance workspace</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/settings" className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-800">Settings</Link>
          <Link to="/advisor" className="rounded-2xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500">AI Advisor</Link>
        </div>
      </div>
    </header>
  );
}
