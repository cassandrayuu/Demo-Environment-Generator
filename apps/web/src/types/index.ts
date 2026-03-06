export interface ProductInfo {
  id: string;
  name: string;
  componentCount: number;
  featureCount: number;
  eligible?: boolean;
  ineligibleReason?: string | null;
}

export interface SelectedProduct {
  id: string;
  name: string;
}

export interface StepResult {
  name: string;
  status: 'pending' | 'running' | 'success' | 'error' | 'skipped';
  summary: Record<string, unknown>;
  logs: string[];
  error?: string;
}

export interface JobResult {
  jobId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  mode: string;
  company: string;
  website: string;
  selectedProducts: SelectedProduct[];
  steps: StepResult[];
  warnings: string[];
  errors: string[];
  completedAt?: string;
}

export interface AnalyzeRecommendations {
  autoSelectProductIds: string[];
}

export interface AnalyzeResult {
  products: ProductInfo[];
  warnings: string[];
  recommendations: AnalyzeRecommendations;
}

export interface FlexibleOptions {
  maxComponentsPerProduct?: number;
  maxFeaturesPerComponent?: number;
}

export type AppStep = 'input' | 'select' | 'progress';

export interface AppState {
  step: AppStep;
  company: string;
  website: string;
  token: string;
  rememberToken: boolean;
  products: ProductInfo[];
  selectedProductIds: string[];
  jobResult: JobResult | null;
  loading: boolean;
  error: string | null;
  analyzeWarnings: string[];
}
