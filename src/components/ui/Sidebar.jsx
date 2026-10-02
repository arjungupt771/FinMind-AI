import { NavLink } from 'react-router-dom';

const navItems = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Transactions', path: '/transactions' },
  { label: 'Goals', path: '/goals' },
  { label: 'Forecast', path: '/forecast' },
  { label: 'AI Advisor', path: '/advisor' },
  { label: 'Settings', path: '/settings' },
];

export default function Sidebar() {
  return (
    <aside className="w-full max-w-[280px] shrink-0 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-5 shadow-2xl shadow-black/20 lg:h-[calc(100vh-120px)] lg:sticky lg:top-[80px]">
      <div className="mb-8">
        <div className="text-sm uppercase tracking-[0.3em] text-slate-500">Workspace</div>
        <p className="mt-3 text-xl font-semibold text-slate-100">Navigation</p>
      </div>
      <nav className="space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `block rounded-2xl px-4 py-3 text-sm transition ${
                isActive ? 'bg-brand-600 text-white shadow-lg shadow-brand-900/20' : 'text-slate-300 hover:bg-slate-800'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
