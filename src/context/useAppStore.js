import create from 'zustand';
import { persist } from 'zustand/middleware';
import { categorizeTransaction } from '../services/categorizationService';
import { parseFile, normalizeTransactions } from '../services/parserService';
import { buildOverview, computeHealthScore, detectAnomalies, detectSubscriptions, predictGoals, buildForecast } from '../services/analyticsService';

const useAppStore = create(
  persist(
    (set, get) => ({
      transactions: [],
      uploads: [],
      goals: [],
      apiKey: '',
      insights: [],
      setApiKey: (key) => set({ apiKey: key }),
      loadState: () => {
        const transactions = JSON.parse(localStorage.getItem('finmind_transactions') || '[]');
        const uploads = JSON.parse(localStorage.getItem('finmind_uploads') || '[]');
        const goals = JSON.parse(localStorage.getItem('finmind_goals') || '[]');
        set({ transactions, uploads, goals });
      },
      addTransactions: async (file) => {
        const parsed = await parseFile(file);
        const normalized = normalizeTransactions(parsed);
        const existing = get().transactions;
        const unique = [...existing, ...normalized].map((tx, index) => ({
          ...tx,
          id: tx.id || `tx_${Date.now()}_${index}`,
          createdAt: tx.createdAt || new Date().toISOString(),
        }));
        const keyed = new Map();
        unique.forEach((tx) => {
          const key = `${tx.date}|${tx.merchant}|${tx.amount}|${tx.category}`;
          if (!keyed.has(key)) keyed.set(key, tx);
        });
        const transactions = Array.from(keyed.values());
        const uploads = [{
          id: `upload_${Date.now()}`,
          fileName: parsed.sourceFile,
          transactionCount: normalized.length,
          uploadedAt: new Date().toISOString(),
          sourceType: parsed.mimeType,
          status: 'Parsed',
        },
          ...get().uploads,
        ];
        localStorage.setItem('finmind_transactions', JSON.stringify(transactions));
        localStorage.setItem('finmind_uploads', JSON.stringify(uploads));
        set({ transactions, uploads });
        return normalized.length;
      },
      createGoal: (goal) => {
        const goals = [...get().goals, { id: `goal_${Date.now()}`, ...goal }];
        localStorage.setItem('finmind_goals', JSON.stringify(goals));
        set({ goals });
      },
      removeGoal: (goalId) => {
        const goals = get().goals.filter((goal) => goal.id !== goalId);
        localStorage.setItem('finmind_goals', JSON.stringify(goals));
        set({ goals });
      },
      calculateOverview: () => buildOverview(get().transactions),
      calculateHealth: () => computeHealthScore(get().transactions),
      calculateAnomalies: () => detectAnomalies(get().transactions),
      calculateSubscriptions: () => detectSubscriptions(get().transactions),
      calculateGoals: () => predictGoals(get().goals, get().transactions),
      calculateForecast: (horizon) => buildForecast(get().transactions, horizon),
    }),
    {
      name: 'finmind-store',
      partialize: (state) => ({
        transactions: state.transactions,
        uploads: state.uploads,
        goals: state.goals,
        apiKey: state.apiKey,
      }),
    }
  )
);

export default useAppStore;
