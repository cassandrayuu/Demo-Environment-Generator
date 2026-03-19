/**
 * Insights API routes
 */

import type { Env } from "../types";

interface GenerateInsightsRequest {
  company: string;
  website: string;
  token: string;
  count: number;
}

/**
 * POST /api/insights
 *
 * Proxy streaming request to runner for insights generation.
 */
export async function handleGenerateInsights(
  request: Request,
  env: Env
): Promise<Response> {
  try {
    const body = (await request.json()) as GenerateInsightsRequest;

    // Validate required fields
    if (!body.company || !body.website || !body.token) {
      return new Response(
        JSON.stringify({ error: "Missing required fields: company, website, token" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Validate count
    const count = body.count || 10;
    if (count < 1 || count > 50) {
      return new Response(
        JSON.stringify({ error: "Count must be between 1 and 50" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Proxy to runner with streaming
    const runnerResponse = await fetch(`${env.RUNNER_URL}/api/insights`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.RUNNER_SECRET}`,
      },
      body: JSON.stringify({
        company: body.company,
        website: body.website,
        token: body.token,
        count: count,
      }),
    });

    // Stream the response back
    return new Response(runnerResponse.body, {
      status: runnerResponse.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("Error generating insights:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to generate insights",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
