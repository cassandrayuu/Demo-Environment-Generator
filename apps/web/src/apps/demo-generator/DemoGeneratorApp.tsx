import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { StepIndicator } from '../../components/StepIndicator';
import { InputPage } from './pages/InputPage';
import { SelectPage } from './pages/SelectPage';
import { ProgressPage } from './pages/ProgressPage';
import {
  analyzeSpace,
  runJobStreaming,
  StepUpdate,
  saveToken,
  loadToken,
  clearToken,
} from '../../api/client';
import type { AppState } from '../../types';

interface CompletedStep {
  name: string;
  label: string;
  status: 'success' | 'error';
}

const getInitialState = (): AppState => {
  const savedToken = loadToken();
  return {
    step: 'input',
    company: '',
    website: '',
    token: savedToken || '',
    rememberToken: !!savedToken,
    products: [],
    selectedProductIds: [],
    includeStrategy: true, // Enabled by default
    jobResult: null,
    loading: false,
    error: null,
    analyzeWarnings: [],
  };
};

const stepLabels: Record<string, string> = {
  analyze_structure: 'Analyzing space structure...',
  generate_mappings: 'Generating mappings...',
  validate_preflight: 'Validating configuration...',
  rename_hierarchy: 'Renaming product hierarchy...',
  rename_strategy: 'Renaming strategic hierarchy...',
  generate_insights: 'Generating insights...',
};

export function DemoGeneratorApp() {
  const [state, setState] = useState<AppState>(getInitialState);
  const [completedSteps, setCompletedSteps] = useState<CompletedStep[]>([]);
  const [currentStep, setCurrentStep] = useState<string | null>(null);

  const updateState = (updates: Partial<AppState>) => {
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

  const handleConnect = async () => {
    updateState({ loading: true, error: null });

    try {
      const result = await analyzeSpace(state.token, state.company, state.website);

      // Auto-select recommended products
      const autoSelectIds = result.recommendations.autoSelectProductIds || [];

      updateState({
        products: result.products,
        selectedProductIds: autoSelectIds,
        analyzeWarnings: result.warnings,
        step: 'select',
        loading: false,
      });
    } catch (err) {
      updateState({
        error: err instanceof Error ? err.message : 'Failed to analyze space',
        loading: false,
      });
    }
  };

  const handleToggleProduct = (productId: string) => {
    const current = state.selectedProductIds;
    const updated = current.includes(productId)
      ? current.filter((id) => id !== productId)
      : current.length < 2
      ? [...current, productId]
      : current;
    updateState({ selectedProductIds: updated });
  };

  const handleGenerate = async () => {
    updateState({ loading: true, error: null, step: 'progress' });
    setCompletedSteps([]);
    setCurrentStep(null);

    const handleStep = (step: StepUpdate) => {
      // Show what's running
      setCurrentStep(stepLabels[step.name] || step.name);

      // Add to completed when done
      if (step.status === 'success' || step.status === 'error') {
        const labels: Record<string, string> = {
          analyze_structure: 'Structure analyzed',
          generate_mappings: 'Mappings generated',
          validate_preflight: 'Configuration validated',
          rename_hierarchy: 'Product hierarchy renamed',
          rename_strategy: 'Strategic hierarchy renamed',
          generate_insights: 'Insights generated',
        };
        setCompletedSteps((prev) => [
          ...prev,
          {
            name: step.name,
            label: labels[step.name] || step.name,
            status: step.status as 'success' | 'error',
          },
        ]);
      }
    };

    const handleComplete = (result: typeof state.jobResult) => {
      setCurrentStep(null);
      updateState({
        jobResult: result,
        loading: false,
      });
    };

    const handleError = (error: string) => {
      setCurrentStep(null);
      updateState({
        error,
        loading: false,
        jobResult: {
          jobId: '',
          status: 'failed',
          mode: 'apply',
          company: state.company,
          website: state.website,
          selectedProducts: [],
          steps: [],
          warnings: [],
          errors: [error],
        },
      });
    };

    try {
      await runJobStreaming(
        {
          company: state.company,
          website: state.website,
          token: state.token,
          selectedProductIds: state.selectedProductIds,
          includeStrategy: state.includeStrategy,
        },
        handleStep,
        handleComplete,
        handleError
      );
    } catch (err) {
      handleError(err instanceof Error ? err.message : 'Job failed');
    }
  };

  const handleRunAgain = () => {
    setState({
      ...getInitialState(),
      token: state.token,
      rememberToken: state.rememberToken,
    });
    setCompletedSteps([]);
    setCurrentStep(null);
  };

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
          <h1 className="text-2xl font-semibold mb-2">
            Productboard Demo Generator
          </h1>
          <p className="text-gray-400 text-sm">
            Set up a demo environment for your prospect
          </p>
        </div>

        <StepIndicator currentStep={state.step} />

        {state.step === 'input' && (
          <InputPage
            company={state.company}
            website={state.website}
            token={state.token}
            rememberToken={state.rememberToken}
            loading={state.loading}
            error={state.error}
            onCompanyChange={(company) => updateState({ company })}
            onWebsiteChange={(website) => updateState({ website })}
            onTokenChange={(token) => updateState({ token })}
            onRememberTokenChange={(rememberToken) => updateState({ rememberToken })}
            onClearToken={handleClearToken}
            onConnect={handleConnect}
          />
        )}

        {state.step === 'select' && (
          <SelectPage
            company={state.company}
            products={state.products}
            selectedProductIds={state.selectedProductIds}
            includeStrategy={state.includeStrategy}
            loading={state.loading}
            error={state.error}
            analyzeWarnings={state.analyzeWarnings}
            onToggleProduct={handleToggleProduct}
            onToggleStrategy={(includeStrategy) => updateState({ includeStrategy })}
            onBack={() => updateState({ step: 'input', error: null })}
            onGenerate={handleGenerate}
          />
        )}

        {state.step === 'progress' && (
          <ProgressPage
            company={state.company}
            jobResult={state.jobResult}
            completedSteps={completedSteps}
            currentStep={currentStep}
            onBack={() => updateState({ step: 'select', error: null })}
            onRunAgain={handleRunAgain}
          />
        )}
      </div>
    </div>
  );
}
