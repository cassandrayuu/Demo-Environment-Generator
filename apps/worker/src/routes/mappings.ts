/**
 * Mappings API routes
 */

import type { Env, GenerateMappingsRequest } from "../types";

/**
 * POST /api/mappings/generate
 *
 * Proxy request to runner to generate mappings
 */
export async function handleGenerateMappings(
  request: Request,
  env: Env
): Promise<Response> {
  try {
    const body = (await request.json()) as GenerateMappingsRequest;

    if (!body.company || !body.website) {
      return new Response(
        JSON.stringify({ error: "Missing company or website" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Proxy to runner
    const runnerResponse = await fetch(`${env.RUNNER_URL}/mappings/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.RUNNER_SECRET}`,
      },
      body: JSON.stringify({
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
    console.error("Error generating mappings:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to generate mappings",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
