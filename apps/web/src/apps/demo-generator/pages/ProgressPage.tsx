import { useState } from 'react';
import type { JobResult, StepResult } from '../../../types';

interface ParsedChanges {
  products: string[];
  components: string[];
  features: string[];
  objectives: string[];
  keyResults: string[];
  initiatives: string[];
  notesCount: number;
}

function parseChangesFromSteps(steps: StepResult[]): ParsedChanges {
  const changes: ParsedChanges = {
    products: [],
    components: [],
    features: [],
    objectives: [],
    keyResults: [],
    initiatives: [],
    notesCount: 0,
  };

  // Parse rename_hierarchy step logs
  const hierarchyStep = steps.find(s => s.name === 'rename_hierarchy');
  if (hierarchyStep) {
    for (const log of hierarchyStep.logs) {
      // Match: [Product] 'Old Name' -> 'New Name' - Updated
      const match = log.match(/\[(Product|Component|Feature)\].*?-> '(.+?)' - Updated/);
      if (match) {
        const [, type, newName] = match;
        if (type === 'Product') changes.products.push(newName);
        else if (type === 'Component') changes.components.push(newName);
        else if (type === 'Feature') changes.features.push(newName);
      }
    }
  }

  // Parse rename_strategy step logs
  const strategyStep = steps.find(s => s.name === 'rename_strategy');
  if (strategyStep) {
    for (const log of strategyStep.logs) {
      // Match: [Objective] 'Old Name' -> 'New Name' - Updated
      const match = log.match(/\[(Objective|Key Result|Initiative)\].*?-> '(.+?)' - Updated/);
      if (match) {
        const [, type, newName] = match;
        if (type === 'Objective') changes.objectives.push(newName);
        else if (type === 'Key Result') changes.keyResults.push(newName);
        else if (type === 'Initiative') changes.initiatives.push(newName);
      }
    }
  }

  // Parse generate_insights step for notes count
  const insightsStep = steps.find(s => s.name === 'generate_insights');
  if (insightsStep?.summary && typeof insightsStep.summary === 'object') {
    const summary = insightsStep.summary as Record<string, unknown>;
    if (typeof summary.created === 'number') {
      changes.notesCount = summary.created;
    }
  }

  return changes;
}

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

function ChangeSummary({ changes, steps, showLogs, onToggleLogs }: {
  changes: ParsedChanges;
  steps: StepResult[];
  showLogs: boolean;
  onToggleLogs: () => void;
}) {
  const stats = [
    { label: 'Products', value: changes.products.length },
    { label: 'Components', value: changes.components.length },
    { label: 'Features', value: changes.features.length },
    { label: 'Objectives', value: changes.objectives.length },
    { label: 'Initiatives', value: changes.initiatives.length },
    { label: 'Notes', value: changes.notesCount },
  ].filter(s => s.value > 0);

  const hasChanges = stats.length > 0;

  // Collect all logs from rename steps
  const allLogs: string[] = [];
  const hierarchyStep = steps.find(s => s.name === 'rename_hierarchy');
  const strategyStep = steps.find(s => s.name === 'rename_strategy');
  if (hierarchyStep) allLogs.push(...hierarchyStep.logs);
  if (strategyStep) allLogs.push(...strategyStep.logs);

  if (!hasChanges) return null;

  return (
    <div className="mt-6 pt-6 border-t border-gray-700">
      {/* Section title */}
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-4">
        <svg className="w-4 h-4 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
        Changes Applied
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {stats.map(stat => (
          <div key={stat.label} className="bg-gray-900 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-gray-100">{stat.value}</div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* New entity names */}
      {changes.products.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">New Products</div>
          <div className="flex flex-wrap gap-2">
            {changes.products.map((name, i) => (
              <span key={i} className="px-3 py-1.5 bg-primary-500/15 border border-primary-500/30 text-primary-400 text-sm rounded-md">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {changes.objectives.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">New Objectives</div>
          <div className="flex flex-wrap gap-2">
            {changes.objectives.map((name, i) => (
              <span key={i} className="px-3 py-1.5 bg-gray-700 text-gray-200 text-sm rounded-md">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {changes.initiatives.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">New Initiatives</div>
          <div className="flex flex-wrap gap-2">
            {changes.initiatives.slice(0, 5).map((name, i) => (
              <span key={i} className="px-3 py-1.5 bg-gray-700 text-gray-200 text-sm rounded-md">
                {name}
              </span>
            ))}
            {changes.initiatives.length > 5 && (
              <span className="px-3 py-1.5 text-gray-400 text-sm">
                +{changes.initiatives.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Expandable logs */}
      {allLogs.length > 0 && (
        <>
          <button
            onClick={onToggleLogs}
            className="w-full mt-4 py-3 px-4 border border-gray-700 rounded-lg text-gray-400 text-sm flex items-center justify-center gap-2 hover:border-gray-600 hover:text-gray-300 transition-colors"
          >
            <svg
              className={`w-4 h-4 transition-transform ${showLogs ? 'rotate-180' : ''}`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
            {showLogs ? 'Hide' : 'View'} Detailed Change Log
          </button>

          {showLogs && (
            <div className="mt-3 p-3 bg-gray-900 rounded-lg max-h-64 overflow-y-auto">
              <div className="text-xs font-mono text-gray-400 space-y-1">
                {allLogs.map((log, i) => (
                  <div key={i} className={log.includes('Updated') ? 'text-green-400' : ''}>
                    {log}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function ProgressPage({
  jobResult,
  completedSteps,
  currentStep,
  onBack,
  onRunAgain,
}: ProgressPageProps) {
  const [showLogs, setShowLogs] = useState(false);

  const isComplete =
    jobResult?.status === 'completed' || jobResult?.status === 'failed';
  const isSuccess = jobResult?.status === 'completed';

  const changes = jobResult ? parseChangesFromSteps(jobResult.steps) : null;

  const copyResults = () => {
    if (!jobResult) return;

    const summary = [
      `Productboard Demo Generator - Results`,
      `=====================================`,
      `Company: ${jobResult.company}`,
      `Website: ${jobResult.website}`,
      `Status: ${jobResult.status}`,
    ];

    // Add change statistics
    if (changes) {
      summary.push(``, `Changes Applied:`);
      if (changes.products.length > 0) summary.push(`  Products renamed: ${changes.products.length}`);
      if (changes.components.length > 0) summary.push(`  Components renamed: ${changes.components.length}`);
      if (changes.features.length > 0) summary.push(`  Features renamed: ${changes.features.length}`);
      if (changes.objectives.length > 0) summary.push(`  Objectives renamed: ${changes.objectives.length}`);
      if (changes.initiatives.length > 0) summary.push(`  Initiatives renamed: ${changes.initiatives.length}`);
      if (changes.notesCount > 0) summary.push(`  Notes created: ${changes.notesCount}`);

      if (changes.products.length > 0) {
        summary.push(``, `New Products:`);
        changes.products.forEach(p => summary.push(`  - ${p}`));
      }
      if (changes.objectives.length > 0) {
        summary.push(``, `New Objectives:`);
        changes.objectives.forEach(o => summary.push(`  - ${o}`));
      }
      if (changes.initiatives.length > 0) {
        summary.push(``, `New Initiatives:`);
        changes.initiatives.forEach(i => summary.push(`  - ${i}`));
      }
    }

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

            {/* Changes summary */}
            {changes && jobResult && (
              <ChangeSummary
                changes={changes}
                steps={jobResult.steps}
                showLogs={showLogs}
                onToggleLogs={() => setShowLogs(!showLogs)}
              />
            )}

            {/* Warnings (only if any) */}
            {jobResult?.warnings && jobResult.warnings.length > 0 && (
              <div className="mt-6 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
                <div className="text-sm font-medium text-yellow-400 mb-2">Notes</div>
                {jobResult.warnings.map((w, i) => (
                  <div key={i} className="text-sm text-yellow-300/80">• {w}</div>
                ))}
              </div>
            )}

            {/* Primary action */}
            <button
              className="btn btn-primary w-full mt-6"
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
