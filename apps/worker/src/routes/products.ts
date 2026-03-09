/**
 * Products API routes
 */

import type { Env, ListProductsRequest, AnalyzeRequest } from "../types";

/**
 * POST /api/products/list
 *
 * Proxy request to runner to list products in a PB space
 */
export async function handleListProducts(
  request: Request,
  env: Env
): Promise<Response> {
  try {
    const body = (await request.json()) as ListProductsRequest;

    if (!body.token) {
      return new Response(
        JSON.stringify({ error: "Missing token" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Proxy to runner
    const runnerResponse = await fetch(`${env.RUNNER_URL}/api/products/list`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.RUNNER_SECRET}`,
      },
      body: JSON.stringify({ token: body.token }),
    });

    const data = await runnerResponse.json();

    return new Response(JSON.stringify(data), {
      status: runnerResponse.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error listing products:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to list products",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

/**
 * POST /api/analyze
 *
 * Analyze a Productboard space - returns products with eligibility and recommendations
 */
export async function handleAnalyzeSpace(
  request: Request,
  env: Env
): Promise<Response> {
  try {
    const body = (await request.json()) as AnalyzeRequest;

    if (!body.token) {
      return new Response(
        JSON.stringify({ error: "Missing token" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    if (!body.company || !body.website) {
      return new Response(
        JSON.stringify({ error: "Missing company or website" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Proxy to runner
    const runnerResponse = await fetch(`${env.RUNNER_URL}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.RUNNER_SECRET}`,
      },
      body: JSON.stringify({
        token: body.token,
        company: body.company,
        website: body.website,
      }),
    });

    const data = await runnerResponse.json();

    return new Response(JSON.stringify(data), {
      status: runnerResponse.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error analyzing space:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to analyze space",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
