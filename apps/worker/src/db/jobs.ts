/**
 * Job database operations
 */

import type { JobRecord, JobResult, SelectedProduct } from "../types";

/**
 * Create a new job record
 */
export async function createJob(
  db: D1Database,
  data: {
    id: string;
    userEmail: string;
    company: string;
    website: string;
    selectedProducts: SelectedProduct[];
    mode: string;
  }
): Promise<void> {
  const now = new Date().toISOString();

  await db
    .prepare(
      `INSERT INTO jobs (id, user_email, company, website, selected_products, mode, status, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)`
    )
    .bind(
      data.id,
      data.userEmail,
      data.company,
      data.website,
      JSON.stringify(data.selectedProducts),
      data.mode,
      now,
      now
    )
    .run();
}

/**
 * Update job status
 */
export async function updateJobStatus(
  db: D1Database,
  jobId: string,
  status: string,
  result?: JobResult
): Promise<void> {
  const now = new Date().toISOString();

  if (result) {
    await db
      .prepare(
        `UPDATE jobs SET status = ?, result = ?, updated_at = ? WHERE id = ?`
      )
      .bind(status, JSON.stringify(result), now, jobId)
      .run();
  } else {
    await db
      .prepare(`UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?`)
      .bind(status, now, jobId)
      .run();
  }
}

/**
 * Get a job by ID
 */
export async function getJob(
  db: D1Database,
  jobId: string
): Promise<JobRecord | null> {
  const result = await db
    .prepare(`SELECT * FROM jobs WHERE id = ?`)
    .bind(jobId)
    .first<JobRecord>();

  return result;
}

/**
 * List jobs for a user
 */
export async function listJobs(
  db: D1Database,
  userEmail: string,
  limit: number = 20
): Promise<JobRecord[]> {
  const result = await db
    .prepare(
      `SELECT * FROM jobs WHERE user_email = ? ORDER BY created_at DESC LIMIT ?`
    )
    .bind(userEmail, limit)
    .all<JobRecord>();

  return result.results || [];
}

/**
 * Parse job result from database record
 */
export function parseJobResult(record: JobRecord): JobResult | null {
  if (!record.result) return null;

  try {
    return JSON.parse(record.result) as JobResult;
  } catch {
    return null;
  }
}

/**
 * Parse selected products from database record
 */
export function parseSelectedProducts(record: JobRecord): SelectedProduct[] {
  if (!record.selected_products) return [];

  try {
    return JSON.parse(record.selected_products) as SelectedProduct[];
  } catch {
    return [];
  }
}
