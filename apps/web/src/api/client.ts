import type { ProductInfo, JobResult, AnalyzeResult, FlexibleOptions } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface ApiError {
  error: string;
  detail?: string;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    throw new Error('Empty response from server. Is the API running?');
  }

  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON response: ${text.slice(0, 100)}`);
  }

  if (!response.ok) {
    const error = data as ApiError;
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }

  return data as T;
}

/**
 * Analyze a Productboard space - returns products with eligibility and recommendations.
 * This is the new primary entry point that combines listing + analysis.
 */
export async function analyzeSpace(
  token: string,
  company: string,
  website: string
): Promise<AnalyzeResult> {
  return apiRequest<AnalyzeResult>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ token, company, website }),
  });
}

/**
 * List products in a Productboard space.
 * @deprecated Use analyzeSpace instead
 */
export async function listProducts(token: string): Promise<ProductInfo[]> {
  const response = await apiRequest<{ products: ProductInfo[] }>(
    '/api/products/list',
    {
      method: 'POST',
      body: JSON.stringify({ token }),
    }
  );
  return response.products;
}

export interface StepUpdate {
  name: string;
  status: 'success' | 'error' | 'running' | 'skipped' | 'pending';
  summary: Record<string, unknown>;
  error?: string;
}

export interface RunJobParams {
  company: string;
  website: string;
  token: string;
  selectedProductIds: string[];
  options?: FlexibleOptions;
}

/**
 * Run a POC job with streaming progress updates.
 * Always runs in "apply" mode now (no more dry-run as primary).
 */
export async function runJobStreaming(
  params: RunJobParams,
  onStep: (step: StepUpdate) => void,
  onComplete: (result: JobResult) => void,
  onError: (error: string) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...params,
      mode: 'apply', // Always apply now
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    try {
      const error = JSON.parse(text);
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    } catch {
      throw new Error(`HTTP ${response.status}: ${text.slice(0, 100)}`);
    }
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process complete events (each ends with \n\n)
    const events = buffer.split('\n\n');
    buffer = events.pop() || ''; // Keep incomplete event in buffer

    for (const event of events) {
      if (!event.trim()) continue;

      // Parse SSE format: "data: {...}"
      const dataMatch = event.match(/^data: (.+)$/m);
      if (!dataMatch) continue;

      try {
        const data = JSON.parse(dataMatch[1]);

        if (data.type === 'step') {
          onStep(data.step);
        } else if (data.type === 'complete') {
          onComplete(data.result);
        } else if (data.type === 'error') {
          onError(data.error);
        }
      } catch (e) {
        console.error('Failed to parse SSE event:', e);
      }
    }
  }
}

export async function getJob(jobId: string): Promise<JobResult> {
  return apiRequest<JobResult>(`/api/jobs/${jobId}`, {
    method: 'GET',
  });
}

// Token persistence helpers
const TOKEN_STORAGE_KEY = 'pb_demo_generator_token';

export function saveToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch (e) {
    console.error('Failed to save token to localStorage:', e);
  }
}

export function loadToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch (e) {
    console.error('Failed to load token from localStorage:', e);
    return null;
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (e) {
    console.error('Failed to clear token from localStorage:', e);
  }
}
