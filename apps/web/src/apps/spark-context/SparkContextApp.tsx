import { useState } from 'react';
import { Link } from 'react-router-dom';

// Use direct Spark Runner URL to bypass Cloudflare Worker timeout (~30s limit)
const SPARK_RUNNER_URL = import.meta.env.VITE_SPARK_RUNNER_URL || '';

const SPARK_PROMPT = 'Recreate each document in my context folder — do not make edits or run analysis, just recreate.';

function DoneStep({
  folderUrl,
  documents,
  onRunAgain,
}: {
  folderUrl: string | null;
  documents: Array<{ name: string; url: string }>;
  onRunAgain: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(SPARK_PROMPT);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card">
      <div className="py-6">
        {/* Success header */}
        <div className="text-center mb-6">
          <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg
              className="w-7 h-7 text-green-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold mb-1">Your Spark context is ready</h2>
          <p className="text-gray-400 text-sm">
            We created {documents.length} documents in Google Drive.
          </p>
        </div>

        {/* Primary action */}
        {folderUrl && (
          <div className="text-center mb-8">
            <a
              href={folderUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary inline-flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-5 h-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
              Open folder in Drive
            </a>
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-gray-800 my-6" />

        {/* Next step section */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-200 mb-2">Next step: Import into Spark</h3>
          <p className="text-xs text-gray-500 mb-3">
            To recreate your context, use this prompt in Spark:
          </p>

          {/* Copyable prompt box */}
          <div className="relative bg-gray-800/60 border border-gray-700/50 rounded-lg p-3">
            <p className="text-sm text-gray-300 pr-16 leading-relaxed">
              {SPARK_PROMPT}
            </p>
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 px-2.5 py-1.5 text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors flex items-center gap-1.5"
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  Copied
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy
                </>
              )}
            </button>
          </div>

          <p className="text-xs text-gray-600 mt-2">
            Paste this into Spark after connecting your Google Drive integration.
          </p>
        </div>

        {/* Document list (collapsed) */}
        {documents.length > 0 && (
          <details className="mb-6">
            <summary className="text-sm text-gray-400 cursor-pointer hover:text-gray-300 transition-colors">
              View {documents.length} generated documents
            </summary>
            <ul className="mt-3 space-y-1.5 max-h-48 overflow-y-auto pl-4">
              {documents.map((doc, i) => (
                <li key={i}>
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary-400 hover:text-primary-300 hover:underline block truncate"
                  >
                    {doc.name}
                  </a>
                </li>
              ))}
            </ul>
          </details>
        )}

        {/* Actions */}
        <div className="flex gap-3 justify-center">
          <button className="btn btn-secondary" onClick={onRunAgain}>
            Generate Another
          </button>
          <Link to="/" className="btn btn-primary">
            Back to Tools
          </Link>
        </div>
      </div>
    </div>
  );
}

type Step = 'input' | 'progress' | 'done';
type ProgressStep = 'analyzing' | 'generating' | 'creating' | 'uploading';

const PROGRESS_STEPS: { id: ProgressStep; label: string }[] = [
  { id: 'analyzing', label: 'Analyzing company' },
  { id: 'generating', label: 'Generating strategic insights' },
  { id: 'creating', label: 'Creating documents' },
  { id: 'uploading', label: 'Uploading to Google Drive' },
];

interface SparkContextState {
  step: Step;
  company: string;
  website: string;
  loading: boolean;
  error: string | null;
  // Progress state
  progressMessage: string;
  progressPercent: number;
  currentProgressStep: ProgressStep;
  currentDocument: string | null;
  // Result state
  folderUrl: string | null;
  documents: Array<{ name: string; url: string }>;
}

const getInitialState = (): SparkContextState => ({
  step: 'input',
  company: '',
  website: '',
  loading: false,
  error: null,
  progressMessage: '',
  progressPercent: 0,
  currentProgressStep: 'analyzing',
  currentDocument: null,
  folderUrl: null,
  documents: [],
});

export function SparkContextApp() {
  const [state, setState] = useState<SparkContextState>(getInitialState);

  const updateState = (updates: Partial<SparkContextState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  };

  const handleGenerate = async () => {
    updateState({
      loading: true,
      error: null,
      step: 'progress',
      progressMessage: 'Starting generation...',
      progressPercent: 0,
      currentProgressStep: 'analyzing',
      currentDocument: null,
    });

    try {
      const response = await fetch(`${SPARK_RUNNER_URL}/api/spark-context`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prospect_name: state.company,
          domain: state.website,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      let receivedComplete = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          // Skip SSE comments (keepalive pings)
          if (line.startsWith(':')) {
            continue;
          }
          if (line.startsWith('event: ')) {
            continue;
          }
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));

            if (data.step === 'generating') {
              // Map progress to the right step
              const progress = data.progress || 0;
              let currentProgressStep: ProgressStep = 'analyzing';
              if (progress < 20) {
                currentProgressStep = 'analyzing';
              } else if (progress < 70) {
                currentProgressStep = 'generating';
              } else {
                currentProgressStep = 'creating';
              }
              updateState({
                progressMessage: data.message || 'Generating documents...',
                progressPercent: progress,
                currentProgressStep,
              });
            } else if (data.step === 'uploading') {
              updateState({
                progressMessage: data.message || 'Uploading to Google Drive...',
                progressPercent: data.progress || 85,
                currentProgressStep: 'uploading',
                currentDocument: data.name || null,
              });
            } else if (data.folder_url) {
              // Complete event
              receivedComplete = true;
              updateState({
                loading: false,
                step: 'done',
                folderUrl: data.folder_url,
                documents: data.documents || [],
              });
            } else if (data.message && !data.step) {
              // Error event
              receivedComplete = true;
              updateState({
                loading: false,
                error: data.message,
                step: 'input',
              });
            }
          }
        }
      }

      // Handle unexpected stream termination
      if (!receivedComplete) {
        updateState({
          loading: false,
          error: 'Connection lost during generation. The documents may have been created - check your Google Drive folder.',
          step: 'input',
        });
      }
    } catch (err) {
      updateState({
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to generate',
        step: 'input',
      });
    }
  };

  const handleRunAgain = () => {
    setState(getInitialState());
  };

  const isValid = state.company.trim() && state.website.trim();

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
          <h1 className="text-2xl font-semibold mb-2">Spark Context Generator</h1>
          <p className="text-gray-400 text-sm">
            Generate strategic intelligence documents for Spark pre-meeting research
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
                  placeholder="e.g., Acme Corp"
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
                  placeholder="https://acme.com"
                  value={state.website}
                  onChange={(e) => updateState({ website: e.target.value })}
                  disabled={state.loading}
                />
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
                {state.loading ? 'Generating...' : 'Generate Context Documents'}
              </button>

              <p className="text-xs text-gray-500 text-center">
                This will generate ~12 strategic documents and save them to Google Drive.
                Generation takes 5-10 minutes.
              </p>
            </div>
          </div>
        )}

        {/* Progress Step */}
        {state.step === 'progress' && (
          <div className="card">
            <div className="py-8">
              {/* Header */}
              <div className="text-center mb-8">
                <div className="w-12 h-12 mx-auto mb-4">
                  <svg viewBox="0 0 24 24" fill="none" className="w-full h-full animate-pulse">
                    <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" fill="url(#spark-progress)" />
                    <defs>
                      <linearGradient id="spark-progress" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                        <stop stopColor="#818cf8" />
                        <stop offset="1" stopColor="#c084fc" />
                      </linearGradient>
                    </defs>
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-gray-100 mb-2">
                  Generating your Spark context
                </h2>
                <p className="text-sm text-gray-500 max-w-sm mx-auto">
                  This usually takes 5–10 minutes. Feel free to grab a coffee — we're generating detailed research and documents for your meeting.
                </p>
              </div>

              {/* Step-based progress */}
              <div className="space-y-3 mb-6">
                {PROGRESS_STEPS.map((progressStep, index) => {
                  const currentIndex = PROGRESS_STEPS.findIndex(s => s.id === state.currentProgressStep);
                  const isCompleted = index < currentIndex;
                  const isCurrent = index === currentIndex;

                  return (
                    <div
                      key={progressStep.id}
                      className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
                        isCurrent ? 'bg-primary-500/10' : ''
                      }`}
                    >
                      {/* Status icon */}
                      <div className="flex-shrink-0">
                        {isCompleted ? (
                          <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                            <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        ) : isCurrent ? (
                          <div className="w-5 h-5 rounded-full bg-primary-500/20 flex items-center justify-center">
                            <div className="w-2 h-2 rounded-full bg-primary-400 animate-pulse" />
                          </div>
                        ) : (
                          <div className="w-5 h-5 rounded-full bg-gray-700/50 flex items-center justify-center">
                            <div className="w-1.5 h-1.5 rounded-full bg-gray-600" />
                          </div>
                        )}
                      </div>

                      {/* Label */}
                      <span
                        className={`text-sm ${
                          isCompleted
                            ? 'text-gray-400'
                            : isCurrent
                            ? 'text-gray-200 font-medium'
                            : 'text-gray-600'
                        }`}
                      >
                        {progressStep.label}
                      </span>

                      {/* Current step indicator */}
                      {isCurrent && state.currentDocument && (
                        <span className="ml-auto text-xs text-gray-500 truncate max-w-[150px]">
                          {state.currentDocument}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Progress bar */}
              <div className="px-4">
                <div className="w-full bg-gray-800 rounded-full h-1">
                  <div
                    className="bg-gradient-to-r from-indigo-500 to-purple-500 h-1 rounded-full transition-all duration-500"
                    style={{ width: `${state.progressPercent}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Done Step */}
        {state.step === 'done' && (
          <DoneStep
            folderUrl={state.folderUrl}
            documents={state.documents}
            onRunAgain={handleRunAgain}
          />
        )}
      </div>
    </div>
  );
}
