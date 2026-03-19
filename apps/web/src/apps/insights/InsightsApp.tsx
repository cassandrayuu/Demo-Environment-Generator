import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  generateInsightsStreaming,
  InsightsProgressEvent,
  InsightsCompleteEvent,
  saveToken,
  loadToken,
  clearToken,
} from '../../api/client';

type Step = 'input' | 'progress' | 'done';

interface InsightsState {
  step: Step;
  company: string;
  website: string;
  token: string;
  rememberToken: boolean;
  count: number;
  loading: boolean;
  error: string | null;
  // Progress state
  currentNote: number;
  totalNotes: number;
  lastNote: string | null;
  // Result state
  createdCount: number;
  failedCount: number;
}

const getInitialState = (): InsightsState => {
  const savedToken = loadToken();
  return {
    step: 'input',
    company: '',
    website: '',
    token: savedToken || '',
    rememberToken: !!savedToken,
    count: 10,
    loading: false,
    error: null,
    currentNote: 0,
    totalNotes: 0,
    lastNote: null,
    createdCount: 0,
    failedCount: 0,
  };
};

export function InsightsApp() {
  const [state, setState] = useState<InsightsState>(getInitialState);

  const updateState = (updates: Partial<InsightsState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  };

  // Handle token persistence
  useEffect(() => {
    if (state.rememberToken && state.token) {
      saveToken(state.token);
    }
  }, [state.rememberToken, state.token]);

  const handleClearToken = () => {
    clearToken();
    updateState({ token: '', rememberToken: false });
  };

  const handleGenerate = async () => {
    updateState({
      loading: true,
      error: null,
      step: 'progress',
      currentNote: 0,
      totalNotes: state.count,
      lastNote: null,
    });

    const handleProgress = (event: InsightsProgressEvent) => {
      updateState({
        currentNote: event.current,
        totalNotes: event.total,
        lastNote: event.note || null,
      });
    };

    const handleComplete = (event: InsightsCompleteEvent) => {
      updateState({
        loading: false,
        step: 'done',
        createdCount: event.created,
        failedCount: event.failed || 0,
      });
    };

    const handleError = (error: string) => {
      updateState({
        loading: false,
        error,
        step: 'input',
      });
    };

    try {
      await generateInsightsStreaming(
        {
          company: state.company,
          website: state.website,
          token: state.token,
          count: state.count,
        },
        handleProgress,
        handleComplete,
        handleError
      );
    } catch (err) {
      handleError(err instanceof Error ? err.message : 'Failed to generate insights');
    }
  };

  const handleRunAgain = () => {
    setState({
      ...getInitialState(),
      token: state.token,
      rememberToken: state.rememberToken,
    });
  };

  const isValid = state.company.trim() && state.website.trim() && state.token.trim();

  return (
    <div className="min-h-screen py-10 px-4">
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-8">
          <Link
            to="/"
            className="text-gray-400 hover:text-gray-200 text-sm mb-4 inline-block"
          >
            &larr; Back to tools
          </Link>
          <h1 className="text-2xl font-semibold mb-2">Insights Generator</h1>
          <p className="text-gray-400 text-sm">
            Generate realistic customer feedback notes for your Productboard space
          </p>
        </div>

        {/* Input Step */}
        {state.step === 'input' && (
          <div className="card">
            <div className="space-y-5">
              <div>
                <label className="label">Company Name</label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g., Instagram"
                  value={state.company}
                  onChange={(e) => updateState({ company: e.target.value })}
                  disabled={state.loading}
                />
              </div>

              <div>
                <label className="label">Website URL</label>
                <input
                  type="url"
                  className="input"
                  placeholder="https://instagram.com"
                  value={state.website}
                  onChange={(e) => updateState({ website: e.target.value })}
                  disabled={state.loading}
                />
              </div>

              <div>
                <label className="label">Productboard API Token</label>
                <input
                  type="password"
                  className="input"
                  placeholder="pb_xxx..."
                  value={state.token}
                  onChange={(e) => updateState({ token: e.target.value })}
                  disabled={state.loading}
                />
              </div>

              <div>
                <label className="label">Number of Notes: {state.count}</label>
                <input
                  type="range"
                  min={5}
                  max={50}
                  step={5}
                  value={state.count}
                  onChange={(e) => updateState({ count: parseInt(e.target.value, 10) })}
                  disabled={state.loading}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>5</span>
                  <span>10</span>
                  <span>20</span>
                  <span>30</span>
                  <span>40</span>
                  <span>50</span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-800"
                    checked={state.rememberToken}
                    onChange={(e) => updateState({ rememberToken: e.target.checked })}
                    disabled={state.loading}
                  />
                  Remember token on this device
                </label>

                {state.token && (
                  <button
                    type="button"
                    className="text-sm text-gray-400 hover:text-red-400 transition-colors"
                    onClick={handleClearToken}
                    disabled={state.loading}
                  >
                    Clear saved token
                  </button>
                )}
              </div>

              {state.error && (
                <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
                  {state.error}
                </div>
              )}

              <button
                className="btn btn-primary w-full"
                onClick={handleGenerate}
                disabled={!isValid || state.loading}
              >
                {state.loading ? 'Generating...' : 'Generate Insights'}
              </button>
            </div>
          </div>
        )}

        {/* Progress Step */}
        {state.step === 'progress' && (
          <div className="card">
            <div className="text-center py-8">
              <div className="mb-6">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary-500/20 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-primary-500 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold mb-2">Generating Insights</h2>
                <p className="text-gray-400">
                  Creating note {state.currentNote} of {state.totalNotes}...
                </p>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-gray-700 rounded-full h-2 mb-4">
                <div
                  className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: `${(state.currentNote / state.totalNotes) * 100}%`,
                  }}
                />
              </div>

              {state.lastNote && (
                <p className="text-sm text-gray-500 truncate px-4">
                  Last: {state.lastNote}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Done Step */}
        {state.step === 'done' && (
          <div className="card">
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-green-500"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h2 className="text-xl font-semibold mb-2">Insights Generated!</h2>
              <p className="text-gray-400 mb-6">
                Successfully created {state.createdCount} feedback notes
                {state.failedCount > 0 && (
                  <span className="text-yellow-500">
                    {' '}
                    ({state.failedCount} failed)
                  </span>
                )}
              </p>

              <div className="flex gap-3 justify-center">
                <button
                  className="btn btn-secondary"
                  onClick={handleRunAgain}
                >
                  Generate More
                </button>
                <Link to="/" className="btn btn-primary">
                  Back to Tools
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
