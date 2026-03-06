/**
 * Productboard Demo Generator - Cloudflare Worker API
 *
 * Edge API that handles authentication, job management, and proxies to the Python runner.
 */

import type { Env } from "./types";
import { verifyAccess, unauthorizedResponse } from "./middleware/auth";
import { handleListProducts, handleAnalyzeSpace } from "./routes/products";
import { handleGenerateMappings } from "./routes/mappings";
import { handleCreateJob, handleGetJob, handleListJobs, handleRunJob } from "./routes/jobs";

/**
 * CORS headers
 */
function corsHeaders(origin: string | null): HeadersInit {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, CF-Access-JWT-Assertion",
    "Access-Control-Max-Age": "86400",
  };
}

/**
 * Handle CORS preflight requests
 */
function handleOptions(request: Request): Response {
  const origin = request.headers.get("Origin");
  return new Response(null, {
    status: 204,
    headers: corsHeaders(origin),
  });
}

/**
 * Add CORS headers to response
 */
function withCors(response: Response, request: Request): Response {
  const origin = request.headers.get("Origin");
  const newHeaders = new Headers(response.headers);

  Object.entries(corsHeaders(origin)).forEach(([key, value]) => {
    newHeaders.set(key, value);
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  });
}

/**
 * Main request handler
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Handle CORS preflight
    if (method === "OPTIONS") {
      return handleOptions(request);
    }

    // Health check (no auth required)
    if (path === "/health" && method === "GET") {
      return withCors(
        new Response(
          JSON.stringify({ status: "healthy", version: "1.0.0" }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        ),
        request
      );
    }

    // All API routes require authentication
    if (path.startsWith("/api/")) {
      const auth = await verifyAccess(request, env);

      if (!auth.authenticated) {
        return withCors(unauthorizedResponse(auth.error || "Unauthorized"), request);
      }

      const userEmail = auth.userEmail || "unknown";

      // Route handling
      let response: Response;

      try {
        // POST /api/products/list
        if (path === "/api/products/list" && method === "POST") {
          response = await handleListProducts(request, env);
        }
        // POST /api/analyze
        else if (path === "/api/analyze" && method === "POST") {
          response = await handleAnalyzeSpace(request, env);
        }
        // POST /api/run (new streaming endpoint)
        else if (path === "/api/run" && method === "POST") {
          response = await handleRunJob(request, env);
        }
        // POST /api/mappings/generate
        else if (path === "/api/mappings/generate" && method === "POST") {
          response = await handleGenerateMappings(request, env);
        }
        // POST /api/jobs (legacy job creation)
        else if (path === "/api/jobs" && method === "POST") {
          response = await handleCreateJob(request, env, userEmail);
        }
        // GET /api/jobs
        else if (path === "/api/jobs" && method === "GET") {
          response = await handleListJobs(env, userEmail);
        }
        // GET /api/jobs/:id
        else if (path.match(/^\/api\/jobs\/[\w-]+$/) && method === "GET") {
          const jobId = path.split("/").pop()!;
          response = await handleGetJob(jobId, env, userEmail);
        }
        // 404
        else {
          response = new Response(
            JSON.stringify({ error: "Not found" }),
            { status: 404, headers: { "Content-Type": "application/json" } }
          );
        }
      } catch (error) {
        console.error("Unhandled error:", error);
        response = new Response(
          JSON.stringify({
            error: "Internal server error",
            detail: error instanceof Error ? error.message : "Unknown error",
          }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      }

      return withCors(response, request);
    }

    // Root redirect to health
    if (path === "/" && method === "GET") {
      return withCors(
        new Response(
          JSON.stringify({
            name: "Productboard Demo Generator API",
            version: "1.0.0",
            docs: "/health",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        ),
        request
      );
    }

    // 404 for other routes
    return withCors(
      new Response(
        JSON.stringify({ error: "Not found" }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      ),
      request
    );
  },
};
