/**
 * Jobs API routes
 */

import type { Env, CreateJobRequest, RunJobRequest, JobResult } from "../types";
import {
  createJob,
  getJob,
  listJobs,
  parseJobResult,
  parseSelectedProducts,
  updateJobStatus,
} from "../db/jobs";

/**
 * Generate a unique job ID
 */
function generateJobId(): string {
  return `job_${crypto.randomUUID().replace(/-/g, "").slice(0, 16)}`;
}

/**
 * POST /api/run
 *
 * Proxy streaming request to runner for direct job execution.
 * This is the new primary endpoint that streams SSE responses.
 */
export async function handleRunJob(
  request: Request,
  env: Env
): Promise<Response> {
  try {
    const body = (await request.json()) as RunJobRequest;

    // Validate required fields
    if (!body.company || !body.website || !body.token) {
      return new Response(
        JSON.stringify({ error: "Missing required fields: company, website, token" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    if (!body.selectedProductIds || body.selectedProductIds.length < 1 || body.selectedProductIds.length > 2) {
      return new Response(
        JSON.stringify({ error: "Must select 1 or 2 products" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Proxy to runner with streaming
    const runnerResponse = await fetch(`${env.RUNNER_URL}/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.RUNNER_SECRET}`,
      },
      body: JSON.stringify({
        company: body.company,
        website: body.website,
        token: body.token,
        selectedProductIds: body.selectedProductIds,
        mode: body.mode || "apply",
        mappings: body.mappings,
        options: body.options,
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
    console.error("Error running job:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to run job",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

/**
 * POST /api/jobs
 *
 * Create and execute a job
 */
export async function handleCreateJob(
  request: Request,
  env: Env,
  userEmail: string
): Promise<Response> {
  try {
    const body = (await request.json()) as CreateJobRequest;

    // Validate required fields
    if (!body.company || !body.website || !body.token) {
      return new Response(
        JSON.stringify({ error: "Missing required fields: company, website, token" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    if (!body.selectedProductIds || body.selectedProductIds.length !== 2) {
      return new Response(
        JSON.stringify({ error: "Must select exactly 2 products" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    const jobId = generateJobId();
    const mode = body.mode || "dry-run";

    // Create job record
    await createJob(env.DB, {
      id: jobId,
      userEmail,
      company: body.company,
      website: body.website,
      selectedProducts: body.selectedProductIds.map((id) => ({ id, name: "" })),
      mode,
    });

    // Update status to running
    await updateJobStatus(env.DB, jobId, "running");

    // Call runner to execute job (synchronously for MVP)
    try {
      const runnerResponse = await fetch(`${env.RUNNER_URL}/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${env.RUNNER_SECRET}`,
        },
        body: JSON.stringify({
          company: body.company,
          website: body.website,
          token: body.token,
          selectedProductIds: body.selectedProductIds,
          mode,
          mappings: body.mappings,
        }),
      });

      if (!runnerResponse.ok) {
        const errorData = await runnerResponse.json().catch(() => ({}));
        throw new Error(
          (errorData as { detail?: string }).detail || `Runner returned ${runnerResponse.status}`
        );
      }

      const result = (await runnerResponse.json()) as JobResult;

      // Update job with result
      const finalStatus = result.errors.length > 0 ? "failed" : "completed";
      await updateJobStatus(env.DB, jobId, finalStatus, result);

      return new Response(
        JSON.stringify({
          jobId,
          status: finalStatus,
          ...result,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    } catch (runnerError) {
      // Update job as failed
      await updateJobStatus(env.DB, jobId, "failed", {
        jobId,
        mode,
        company: body.company,
        website: body.website,
        selectedProducts: [],
        steps: [],
        warnings: [],
        errors: [
          runnerError instanceof Error ? runnerError.message : "Runner execution failed",
        ],
      });

      return new Response(
        JSON.stringify({
          jobId,
          status: "failed",
          error: runnerError instanceof Error ? runnerError.message : "Runner execution failed",
        }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }
  } catch (error) {
    console.error("Error creating job:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to create job",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

/**
 * GET /api/jobs/:id
 *
 * Get job status and result
 */
export async function handleGetJob(
  jobId: string,
  env: Env,
  userEmail: string
): Promise<Response> {
  try {
    const job = await getJob(env.DB, jobId);

    if (!job) {
      return new Response(
        JSON.stringify({ error: "Job not found" }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    // Check user owns this job
    if (job.user_email !== userEmail) {
      return new Response(
        JSON.stringify({ error: "Not authorized to view this job" }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      );
    }

    const result = parseJobResult(job);
    const selectedProducts = parseSelectedProducts(job);

    return new Response(
      JSON.stringify({
        jobId: job.id,
        status: job.status,
        company: job.company,
        website: job.website,
        mode: job.mode,
        selectedProducts,
        createdAt: job.created_at,
        updatedAt: job.updated_at,
        ...(result || {}),
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Error getting job:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to get job",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

/**
 * GET /api/jobs
 *
 * List recent jobs for user
 */
export async function handleListJobs(
  env: Env,
  userEmail: string
): Promise<Response> {
  try {
    const jobs = await listJobs(env.DB, userEmail, 20);

    const jobsList = jobs.map((job) => ({
      jobId: job.id,
      status: job.status,
      company: job.company,
      website: job.website,
      mode: job.mode,
      createdAt: job.created_at,
      updatedAt: job.updated_at,
    }));

    return new Response(
      JSON.stringify({ jobs: jobsList }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Error listing jobs:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to list jobs",
        detail: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
