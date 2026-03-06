import type { AppStep } from '../types';

interface StepIndicatorProps {
  currentStep: AppStep;
}

const steps: { key: AppStep; label: string; name: string }[] = [
  { key: 'input', label: '1', name: 'Setup' },
  { key: 'select', label: '2', name: 'Select Products' },
  { key: 'progress', label: '3', name: 'Generate' },
];

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  const currentIndex = steps.findIndex((s) => s.key === currentStep);

  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {steps.map((step, index) => (
        <div key={step.key} className="flex items-center">
          <div className="flex flex-col items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                index < currentIndex
                  ? 'bg-green-500 text-white'
                  : index === currentIndex
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-700 text-gray-500'
              }`}
            >
              {index < currentIndex ? '✓' : step.label}
            </div>
            <span
              className={`text-xs mt-1 ${
                index <= currentIndex ? 'text-gray-300' : 'text-gray-500'
              }`}
            >
              {step.name}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={`w-10 h-0.5 mx-2 mb-5 ${
                index < currentIndex ? 'bg-green-500' : 'bg-gray-700'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}
