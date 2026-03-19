import type { JobResult } from '../../../types';

interface CompletedStep {
  name: string;
  label: string;
  status: 'success' | 'error';
}

interface ProgressPageProps {
  company: string;
  jobResult: JobResult | null;
  completedSteps: CompletedStep[];
  currentStep: string | null;
  onBack: () => void;
  onRunAgain: () => void;
}

export function ProgressPage({
  jobResult,
  completedSteps,
  currentStep,
  onBack,
  onRunAgain,
}: ProgressPageProps) {
  const isComplete =
    jobResult?.status === 'completed' || jobResult?.status === 'failed';
  const isSuccess = jobResult?.status === 'completed';

  const copyResults = () => {
    if (!jobResult) return;

    const summary = [
      `Productboard Demo Generator - Results`,
      `=====================================`,
      `Company: ${jobResult.company}`,
      `Website: ${jobResult.website}`,
      `Status: ${jobResult.status}`,
    ];

    if (jobResult.warnings.length > 0) {
      summary.push(``, `Warnings:`, ...jobResult.warnings.map(w => `  - ${w}`));
    }

    if (jobResult.errors.length > 0) {
      summary.push(``, `Errors:`, ...jobResult.errors.map(e => `  - ${e}`));
    }

    navigator.clipboard.writeText(summary.join('\n'));
  };

  const openProductboard = () => {
    window.open('https://app.productboard.com', '_blank');
  };

  // Show live progress while job is running
  if (!isComplete) {
    return (
      <div className="space-y-4">
        <button
          className="text-gray-400 hover:text-primary-400 text-sm flex items-center gap-1"
          onClick={onBack}
        >
          ← Back to selection
        </button>

        <div className="card">
          <div className="py-6">
            <h2 className="text-xl font-semibold text-center mb-6">
              Setting up demo environment...
            </h2>

            {/* Completed steps */}
            <div className="space-y-3 mb-4">
              {completedSteps.map((step, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 text-gray-300"
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-medium ${
                      step.status === 'success'
                        ? 'bg-green-500 text-white'
                        : 'bg-red-500 text-white'
                    }`}
                  >
                    {step.status === 'success' ? '✓' : '✗'}
                  </div>
                  <span className="flex-1">{step.label}</span>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      step.status === 'success'
                        ? 'bg-green-600/20 text-green-400'
                        : 'bg-red-600/20 text-red-400'
                    }`}
                  >
                    {step.status === 'success' ? 'Success' : 'Failed'}
                  </span>
                </div>
              ))}
            </div>

            {/* Current step */}
            {currentStep && (
              <div className="flex items-center gap-3 text-primary-400">
                <div className="w-7 h-7 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                <span className="flex-1">{currentStep}</span>
                <span className="text-xs px-2 py-1 rounded bg-primary-600/20 text-primary-400">
                  Running
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <button
        className="text-gray-400 hover:text-primary-400 text-sm flex items-center gap-1"
        onClick={onBack}
      >
        ← Back to selection
      </button>

      <div className="card">
        {isSuccess ? (
          <>
            {/* Success header */}
            <div className="text-center py-8">
              <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-5">
                <span className="text-4xl text-white">✓</span>
              </div>
              <h2 className="text-2xl font-bold text-green-400 mb-2">
                Demo Environment Ready
              </h2>
              <p className="text-gray-400">
                Your Productboard demo environment has been successfully generated.
              </p>
            </div>

            {/* Primary action */}
            <button
              className="btn btn-primary w-full mt-4"
              onClick={openProductboard}
            >
              Open Productboard
            </button>

            {/* Secondary actions */}
            <div className="flex gap-3 mt-3">
              <button className="btn btn-secondary flex-1" onClick={onRunAgain}>
                Generate Another Demo
              </button>
              <button className="btn btn-secondary flex-1" onClick={copyResults}>
                Copy Summary
              </button>
            </div>

            {/* Warnings (only if any) */}
            {jobResult?.warnings && jobResult.warnings.length > 0 && (
              <div className="mt-6 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
                <div className="text-sm font-medium text-yellow-400 mb-2">Notes</div>
                {jobResult.warnings.map((w, i) => (
                  <div key={i} className="text-sm text-yellow-300/80">• {w}</div>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            {/* Error header */}
            <div className="text-center py-6">
              <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl text-white">✗</span>
              </div>
              <h2 className="text-2xl font-bold text-red-400">Setup Failed</h2>
              <p className="text-gray-400 mt-2">
                Something went wrong during configuration
              </p>
            </div>

            {/* Error details */}
            {jobResult?.errors && jobResult.errors.length > 0 && (
              <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mt-4">
                <div className="text-sm text-red-400">
                  {jobResult.errors.map((e, i) => (
                    <div key={i} className="mb-1">• {e}</div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 mt-8">
              <button className="btn btn-secondary flex-1" onClick={copyResults}>
                Copy Summary
              </button>
              <button className="btn btn-primary flex-1" onClick={onRunAgain}>
                Start New
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
