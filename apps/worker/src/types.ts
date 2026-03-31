/**
 * Type definitions for the Cloudflare Worker
 */

export interface Env {
  // D1 Database
  DB: D1Database;

  // Environment variables
  RUNNER_URL: string;
  RUNNER_SECRET: string;
  CF_ACCESS_TEAM_DOMAIN?: string;
  REQUIRE_CLOUDFLARE_ACCESS?: string; // "true" or "false"
  ENVIRONMENT: string;

  // Spark Runner (optional - for Spark Context feature)
  SPARK_RUNNER_URL?: string;
  SPARK_RUNNER_SECRET?: string;
}

// ==================== Request/Response Types ====================

export interface ListProductsRequest {
  token: string;
}

export interface AnalyzeRequest {
  token: string;
  company: string;
  website: string;
}

export interface ProductInfo {
  id: string;
  name: string;
  componentCount: number;
  featureCount: number;
  eligible?: boolean;
  ineligibleReason?: string | null;
}

export interface ListProductsResponse {
  products: ProductInfo[];
}

export interface AnalyzeRecommendations {
  autoSelectProductIds: string[];
}

export interface AnalyzeResponse {
  products: ProductInfo[];
  warnings: string[];
  recommendations: AnalyzeRecommendations;
}

export interface GenerateMappingsRequest {
  company: string;
  website: string;
}

export interface FeatureMapping {
  position: number;
  newName: string;
}

export interface ComponentMapping {
  position: number;
  newName: string;
  features: FeatureMapping[];
}

export interface ProductHierarchyMapping {
  position: number;
  newName: string;
  components: ComponentMapping[];
}

export interface ProductMappingSchema {
  customer: string;
  hierarchy: ProductHierarchyMapping[];
}

export interface KeyResultMapping {
  position: number;
  newName: string;
}

export interface ObjectiveMapping {
  position: number;
  newName: string;
  keyResults: KeyResultMapping[];
}

export interface InitiativeMapping {
  position: number;
  newName: string;
}

export interface StrategyMappingSchema {
  customer: string;
  objectives: ObjectiveMapping[];
  initiatives: InitiativeMapping[];
}

export interface MappingsSchema {
  productMapping: ProductMappingSchema;
  strategyMapping: StrategyMappingSchema;
  features: string[];
}

export interface GenerateMappingsResponse extends MappingsSchema {}

export interface FlexibleOptions {
  maxComponentsPerProduct?: number;
  maxFeaturesPerComponent?: number;
}

export interface CreateJobRequest {
  company: string;
  website: string;
  token: string;
  selectedProductIds: string[];
  mode: "dry-run" | "apply";
  mappings?: MappingsSchema;
  options?: FlexibleOptions;
}

export interface RunJobRequest {
  company: string;
  website: string;
  token: string;
  selectedProductIds: string[];
  mode?: "dry-run" | "apply";
  includeStrategy?: boolean;
  mappings?: MappingsSchema;
  options?: FlexibleOptions;
}

export interface SelectedProduct {
  id: string;
  name: string;
}

export interface StepResult {
  name: string;
  status: "pending" | "running" | "success" | "error" | "skipped";
  summary: Record<string, unknown>;
  logs: string[];
  error?: string;
}

export interface JobResult {
  jobId: string;
  mode: string;
  company: string;
  website: string;
  selectedProducts: SelectedProduct[];
  steps: StepResult[];
  warnings: string[];
  errors: string[];
  completedAt?: string;
}

// ==================== Database Types ====================

export interface JobRecord {
  id: string;
  user_email: string;
  company: string;
  website: string;
  selected_products: string; // JSON
  mode: string;
  status: "pending" | "running" | "completed" | "failed";
  result?: string; // JSON
  created_at: string;
  updated_at: string;
}

// ==================== Cloudflare Access Types ====================

export interface CFAccessJWTPayload {
  aud: string[];
  email: string;
  exp: number;
  iat: number;
  iss: string;
  sub: string;
  type: string;
}
