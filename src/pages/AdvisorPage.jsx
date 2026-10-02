import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import useAppStore from '../context/useAppStore';

const API_BASE = 'http://localhost:8000';

export default function AdvisorPage() {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [chat, setChat] = useState([{
    id: 'welcome',
    from: 'bot',
    text: 'Ask a question about your spending, savings, or goals.',
  }]);
  const [analysisType, setAnalysisType] = useState('general');
  const chatEndRef = useRef(null);
  const transactions = useAppStore((state) => state.transactions);
  const calculateHealth = useAppStore((state) => state.calculateHealth);

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  const analyzeWithGemini = async () => {
    if (!message.trim() || !transactions.length) return;

    const userMessage = message.trim();
    setMessage('');
    
    // Add user message to chat
    setChat((prev) => [...prev, {
      id: `${Date.now()}`,
      from: 'user',
      text: userMessage
    }]);

    // Add loading indicator
    const loadingId = `${Date.now()}-loading`;
    setChat((prev) => [...prev, {
      id: loadingId,
      from: 'bot',
      text: '✨ Analyzing your financial data with Gemini AI...'
    }]);

    setLoading(true);

    try {
      // Prepare context
      const healthScore = calculateHealth();
      const payload = {
        question: userMessage,
        transactions: transactions,
        analysis_type: analysisType,
        context: {},
        health_score: healthScore?.score || 50
      };

      // Call backend chat endpoint
      const response = await axios.post(
        `${API_BASE}/chat/`,
        payload,
        {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 30000 // 30 second timeout
        }
      );

      // Remove loading indicator and add AI response
      setChat((prev) => prev.filter(msg => msg.id !== loadingId));
      
      const aiResponse = response.data;
      setChat((prev) => [...prev, {
        id: `${Date.now()}-bot`,
        from: 'bot',
        text: aiResponse.answer,
        fullResponse: aiResponse
      }]);

    } catch (error) {
      console.error('Chat error:', error);
      
      // Remove loading indicator
      setChat((prev) => prev.filter(msg => msg.id !== loadingId));

      const errorMessage = error.response?.data?.detail 
        || error.message 
        || 'Error processing your request';
      
      setChat((prev) => [...prev, {
        id: `${Date.now()}-error`,
        from: 'bot',
        text: `⚠️ Error: ${errorMessage}. Make sure your Gemini API key is configured in the backend environment.`
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestedPrompt = (prompt) => {
    setMessage(prompt);
    // Auto-submit
    setTimeout(() => {
      // Will submit on next key press or button click
    }, 100);
  };

  const quickActions = [
    { label: 'Where am I overspending?', type: 'spending' },
    { label: 'Can I afford a ₹60,000 laptop?', type: 'budget' },
    { label: 'How much can I invest monthly?', type: 'investment' },
    { label: 'What expenses should I reduce?', type: 'savings' }
  ];

  return (
    <section className="space-y-6">
      <div className="card">
        <h2 className="mb-4 text-xl font-semibold text-slate-100">AI Financial Copilot</h2>
        <p className="mb-6 text-slate-400">Use your data to ask personalized questions powered by Google Gemini AI.</p>
        
        {!transactions.length && (
          <div className="mb-6 rounded-lg border border-yellow-900/50 bg-yellow-950/30 p-4">
            <p className="text-sm text-yellow-200">📊 Upload some transactions first to enable AI analysis.</p>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[0.8fr_0.6fr]">
          {/* Chat Area */}
          <div className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-5 flex flex-col h-96">
            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
              {chat.map((entry) => (
                <div key={entry.id} className={`rounded-3xl p-4 ${entry.from === 'bot' ? 'bg-slate-900 text-slate-200' : 'bg-brand-600/15 text-slate-100'}`}>
                  <div className="text-sm font-semibold text-slate-300">{entry.from === 'bot' ? '🤖 Copilot' : '👤 You'}</div>
                  <div className="mt-2 whitespace-pre-line text-slate-100 text-sm">{entry.text}</div>
                  {entry.fullResponse?.insights && (
                    <div className="mt-3 text-xs text-slate-400">
                      <p className="font-semibold mb-1">💡 Key Insights:</p>
                      <ul className="list-disc list-inside space-y-1">
                        {entry.fullResponse.insights.slice(0, 2).map((insight, i) => (
                          <li key={i}>{insight}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Analysis Type Selector */}
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-5">
              <h3 className="text-lg font-semibold text-slate-100 mb-3">Analysis Type</h3>
              <select
                value={analysisType}
                onChange={(e) => setAnalysisType(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-200 text-sm"
              >
                <option value="general">General Analysis</option>
                <option value="spending">Spending Analysis</option>
                <option value="savings">Savings Tips</option>
                <option value="investment">Investment Advice</option>
                <option value="budget">Budget Optimization</option>
              </select>
            </div>

            {/* Suggested Prompts */}
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/80 p-5">
              <h3 className="text-lg font-semibold text-slate-100 mb-3">Quick Questions</h3>
              <div className="space-y-2">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    type="button"
                    disabled={loading || !transactions.length}
                    onClick={() => {
                      setAnalysisType(action.type);
                      setMessage(action.label);
                    }}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-left text-slate-200 hover:bg-slate-800 disabled:opacity-50 text-sm"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="mt-6 flex flex-col gap-3">
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !loading) {
                  analyzeWithGemini();
                }
              }}
              placeholder="Ask your finance question..."
              disabled={loading || !transactions.length}
              className="flex-1 rounded-lg border border-slate-800/80 bg-slate-900/80 px-4 py-3 text-slate-100 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={analyzeWithGemini}
              disabled={loading || !transactions.length || !message.trim()}
              className="rounded-lg bg-brand-600 px-6 py-3 font-semibold text-white transition hover:bg-brand-500 disabled:opacity-50"
            >
              {loading ? '⏳ Analyzing...' : 'Send'}
            </button>
          </div>
          <p className="text-xs text-slate-500">✨ Powered by Google Gemini 2.5 Flash • API response data flows through backend only</p>
        </div>
      </div>
    </section>
  );
}
