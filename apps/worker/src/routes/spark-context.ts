/**
 * Spark Context proxy routes
 *
 * Proxies requests to the Spark Runner service for strategic intelligence generation.
 */

import type { Env } from "../types";

/**
 * Get the Spark Runner URL from environment
 */
function getSparkRunnerUrl(env: Env): string {
  // Use same runner URL pattern but different port/path for spark
  // For now, assume SPARK_RUNNER_URL env var, fallback to RUNNER_URL with different path
  const sparkUrl = (env as any).SPARK_RUNNER_URL;
  if (sparkUrl) {
    return sparkUrl;
  }
  // Fallback: assume spark-runner is on a different service
  throw new Error("SPARK_RUNNER_URL environment variable not configured");
}

/**
 * Get the Spark Runner secret
 */
function getSparkRunnerSecret(env: Env): string {
  const sparkSecret = (env as any).SPARK_RUNNER_SECRET;
  if (sparkSecret) {
    return sparkSecret;
  }
  // Fallback to main runner secret
  return env.RUNNER_SECRET;
}

/**
 * Proxy SSE request to Spark Runner
 */
async function proxySSE(
  request: Request,
  env: Env,
  path: string
): Promise<Response> {
  const sparkUrl = getSparkRunnerUrl(env);
  const sparkSecret = getSparkRunnerSecret(env);

  // Get request body
  const body = await request.text();

  // Proxy to spark runner
  const response = await fetch(`${sparkUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${sparkSecret}`,
    },
    body,
  });

  // Return SSE stream directly
  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}

/**
 * Handle POST /api/spark-context
 *
 * Generates strategic intelligence documents and uploads to Google Drive.
 * Streams progress via SSE.
 *
 * Request body:
 * {
 *   "company": "Acme Corp",
 *   "website": "https://acme.com"
 * }
 */
export async function handleSparkContextGenerate(
  request: Request,
  env: Env
): Promise<Response> {
  return proxySSE(request, env, "/api/spark-context");
}

/**
 * Handle POST /api/spark-context/smoke
 *
 * Smoke test for Google Drive connectivity.
 */
export async function handleSparkContextSmoke(
  request: Request,
  env: Env
): Promise<Response> {
  return proxySSE(request, env, "/api/spark-context/smoke");
}
