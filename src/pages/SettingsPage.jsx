import useAppStore from '../context/useAppStore';

export default function SettingsPage() {
  const apiKey = useAppStore((state) => state.apiKey);
  const setApiKey = useAppStore((state) => state.setApiKey);

  return (
    <section className="space-y-6">
      <div className="card">
        <h2 className="mb-4 text-xl font-semibold text-slate-100">Platform settings</h2>
        <div className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-6">
          <label className="block text-sm text-slate-400">Gemini API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="mt-3 w-full rounded-3xl border border-slate-800/80 bg-slate-900/80 px-4 py-3 text-slate-100"
            placeholder="Paste your Gemini API key here"
          />
          <p className="mt-3 text-sm text-slate-500">Store your AI key locally to enable financial copilot features. No backend persistence is enabled yet.</p>
        </div>
      </div>
      <div className="card">
        <h2 className="mb-4 text-xl font-semibold text-slate-100">Usage notes</h2>
        <ul className="space-y-3 text-slate-300">
          <li>Upload bank statements in CSV, XLSX, or PDF format.</li>
          <li>Your transaction history is stored in browser local storage.</li>
          <li>AI features are connected to Gemini once you provide a valid key.</li>
          <li>Future backend support will add persistence, auth, and reporting APIs.</li>
        </ul>
      </div>
    </section>
  );
}
