import Anthropic from "@anthropic-ai/sdk";
import type { ProspectInput, GeneratedDocument } from "./types.js";

const client = new Anthropic();

export interface ProgressCallback {
  (event: { type: string; message?: string; progress?: number; batch?: string }): void;
}

export interface BatchResult {
  batch: string;
  documents: GeneratedDocument[];
  error?: string;
}

export interface ParallelGenerationResult {
  folder_name: string;
  completed: GeneratedDocument[];
  failed: { batch: string; error: string }[];
}

// Batch definitions - each batch generates a subset of documents
const BATCHES = [
  {
    id: "company_competitive",
    name: "Company & Competitive Intelligence",
    filePrefix: ["01", "02"],
    prompt: (prospect: ProspectInput) => `Generate the following packets for ${prospect.name} (${prospect.domain}):

1. Company Intelligence Packet (file: "01 - Company Intelligence - ${prospect.name}")
2. Competitive Landscape Packet (file: "02 - Competitive Landscape - ${prospect.name}")

IMPORTANT: Do NOT include metadata headers. Start each document directly with numbered sections.

Output the full packets first, then a JSON object:
{
  "documents": [
    {"file_name": "01 - Company Intelligence - ${prospect.name}", "content": "..."},
    {"file_name": "02 - Competitive Landscape - ${prospect.name}", "content": "..."}
  ]
}`,
    maxTokens: 16000,
  },
  {
    id: "competitors",
    name: "Competitor Deep Dives",
    filePrefix: ["03", "04", "05", "06", "07"],
    prompt: (prospect: ProspectInput) => `Generate 3-5 Competitor Deep Dive packets for ${prospect.name} (${prospect.domain}).

For each major competitor, create a detailed deep dive covering:
1. Snapshot (revenue estimate, funding stage, market focus)
2. Product Model
3. Structural Strengths
4. Structural Weaknesses
5. Win Conditions vs Them
6. Loss Conditions vs Them
7. Recent Strategic Moves
8. AI Positioning

IMPORTANT: Do NOT include metadata headers like "competitor_name:", "overlap_level:", etc. Start each document directly with numbered sections.

Output the full packets first, then a JSON object:
{
  "documents": [
    {"file_name": "03 - Competitor Deep Dive - [Competitor 1]", "content": "..."},
    {"file_name": "04 - Competitor Deep Dive - [Competitor 2]", "content": "..."},
    ...
  ]
}`,
    maxTokens: 24000,
  },
  {
    id: "personas",
    name: "Persona Intelligence",
    filePrefix: ["08", "09", "10", "11", "12", "13"],
    prompt: (prospect: ProspectInput) => `Generate 3-6 Persona Intelligence packets for ${prospect.name} (${prospect.domain}).

Include personas like: economic buyer, operational user, executive stakeholder, technical evaluator.

For each persona, cover:
1. Role Summary
2. KPIs They Care About (quantify where possible)
3. Operational Pressures
4. Budget Authority
5. Current Tool Stack
6. Internal Friction They Face
7. Buying Triggers
8. Objections
9. Messaging That Resonates
10. AI Adoption Psychology

IMPORTANT: Do NOT include metadata headers like "seniority_level:", "economic_buyer:", etc. Start each document directly with numbered sections.

Output the full packets first, then a JSON object:
{
  "documents": [
    {"file_name": "08 - Persona Intelligence - [Role 1]", "content": "..."},
    {"file_name": "09 - Persona Intelligence - [Role 2]", "content": "..."},
    ...
  ]
}`,
    maxTokens: 24000,
  },
  {
    id: "strategic",
    name: "Strategic Intelligence",
    filePrefix: ["14"],
    prompt: (prospect: ProspectInput) => `Generate the Strategic Intelligence packet for ${prospect.name} (${prospect.domain}).

Cover:
1. Vision vs Reality Gap
2. Historical Growth Phases
3. Current Strategic Priorities (Ranked)
4. Estimated Resource Allocation Split (must total 100%)
5. Core Strategic Tensions
6. Expansion Opportunities
7. Execution Risks
8. AI Transformation Levers
9. 3-Year Scenario Outlook (Bull / Base / Bear)

IMPORTANT: Do NOT include metadata headers. Start directly with numbered sections.

Output the full packet first, then a JSON object:
{
  "documents": [
    {"file_name": "14 - Strategic Intelligence - ${prospect.name}", "content": "..."}
  ]
}`,
    maxTokens: 12000,
  },
];

const BATCH_SYSTEM_PROMPT = `You are a strategic intelligence synthesis engine.

PURPOSE
Generate highly realistic, deeply specific intelligence packets for a target company using only company name and domain.

CONSTRAINTS
- NEVER say "information unavailable." Infer plausible assumptions using comparable companies.
- No fluff. No generic summaries. No marketing tone.
- Be analytical, numbers-driven, and concrete.
- Use estimates that are plausible and internally consistent.
- Show tradeoffs, tension, imperfection, risk, churn drivers, and margin pressure.

CRITICAL FORMATTING RULE
Do NOT include metadata blocks at the top of documents. No "packet_type:", "company_name:", "competitor_name:", etc.
Start each document directly with the numbered sections.

DEPTH REQUIREMENTS
- Rich with operational detail: workflows, constraints, and real tradeoffs.
- Use realistic numbers: revenue range, growth, margin profile, budget ranges, KPI targets.
- Include plausible internal conflicts.
- Maintain consistency across all docs.

OUTPUT FORMAT
Output the full packet content first, then a valid JSON object with the documents array.`;

/**
 * Sleep helper for retry backoff
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Generate a single batch with retry logic
 */
async function generateBatch(
  batch: typeof BATCHES[0],
  prospect: ProspectInput,
  onProgress?: ProgressCallback,
  retryCount = 0
): Promise<BatchResult> {
  const maxRetries = 2;
  const model = process.env.ANTHROPIC_MODEL || "claude-sonnet-4-20250514";

  console.log(`[${batch.id}] Starting generation (attempt ${retryCount + 1}/${maxRetries + 1})...`);
  onProgress?.({ type: "batch_start", batch: batch.id, message: `Generating ${batch.name}...` });

  try {
    let fullText = "";
    const stream = client.messages.stream({
      model,
      max_tokens: batch.maxTokens,
      messages: [{ role: "user", content: batch.prompt(prospect) }],
      system: BATCH_SYSTEM_PROMPT,
    });

    for await (const event of stream) {
      if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
        fullText += event.delta.text;
      }
    }

    if (!fullText) {
      throw new Error("No text response from Anthropic");
    }

    // Parse JSON from the response
    const jsonMatch = fullText.match(/\{[\s\S]*"documents"[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error("No valid JSON found in response");
    }

    const parsed = JSON.parse(jsonMatch[0]);
    if (!Array.isArray(parsed.documents)) {
      throw new Error("Invalid documents array in response");
    }

    console.log(`[${batch.id}] SUCCESS: Generated ${parsed.documents.length} documents`);
    onProgress?.({ type: "batch_complete", batch: batch.id, message: `Completed ${batch.name}` });

    return {
      batch: batch.id,
      documents: parsed.documents,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[${batch.id}] FAILED (attempt ${retryCount + 1}): ${errorMessage}`);

    // Retry with exponential backoff
    if (retryCount < maxRetries) {
      const backoffMs = Math.pow(2, retryCount) * 1000; // 1s, 2s
      console.log(`[${batch.id}] Retrying in ${backoffMs}ms...`);
      onProgress?.({ type: "batch_retry", batch: batch.id, message: `Retrying ${batch.name}...` });
      await sleep(backoffMs);
      return generateBatch(batch, prospect, onProgress, retryCount + 1);
    }

    // Max retries exceeded
    console.error(`[${batch.id}] FAILED after ${maxRetries + 1} attempts`);
    return {
      batch: batch.id,
      documents: [],
      error: errorMessage,
    };
  }
}

/**
 * Run batches with concurrency limit using a simple semaphore pattern
 */
async function runBatchesWithConcurrency(
  batches: typeof BATCHES,
  prospect: ProspectInput,
  concurrencyLimit: number,
  onProgress?: ProgressCallback
): Promise<BatchResult[]> {
  // Simple approach: run all batches in parallel (4 batches, limit 3 means minimal queuing)
  // For 4 batches with limit 3, just run them all - the API can handle it
  console.log(`Running ${batches.length} batches with concurrency limit ${concurrencyLimit}...`);

  const batchPromises = batches.map((batch, index) => {
    // Stagger starts slightly to avoid hitting rate limits
    return sleep(index * 500).then(() => generateBatch(batch, prospect, onProgress));
  });

  const results = await Promise.all(batchPromises);
  return results;
}

/**
 * Generate documents in parallel batches
 */
export async function generateDocumentsParallel(
  prospect: ProspectInput,
  onProgress?: ProgressCallback
): Promise<ParallelGenerationResult> {
  console.log(`Starting parallel generation for ${prospect.name}...`);
  onProgress?.({ type: "progress", message: "Starting parallel generation...", progress: 5 });

  const startTime = Date.now();
  const concurrencyLimit = 3; // Max concurrent Anthropic calls

  // Run all batches with concurrency limit
  const batchResults = await runBatchesWithConcurrency(BATCHES, prospect, concurrencyLimit, onProgress);

  // Aggregate results
  const completed: GeneratedDocument[] = [];
  const failed: { batch: string; error: string }[] = [];

  for (const result of batchResults) {
    if (result.error) {
      failed.push({ batch: result.batch, error: result.error });
    } else {
      completed.push(...result.documents);
    }
  }

  // Sort documents by file prefix for consistent ordering
  completed.sort((a, b) => a.file_name.localeCompare(b.file_name));

  const duration = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`Parallel generation complete in ${duration}s. Success: ${completed.length} docs, Failed: ${failed.length} batches`);

  onProgress?.({ type: "progress", message: "Generation complete", progress: 80 });

  return {
    folder_name: prospect.name,
    completed,
    failed,
  };
}

/**
 * Legacy single-call generation (kept for compatibility)
 */
export async function generateDocuments(
  prospect: ProspectInput,
  onProgress?: ProgressCallback
): Promise<string> {
  // Use parallel generation internally
  const result = await generateDocumentsParallel(prospect, onProgress);

  if (result.failed.length > 0 && result.completed.length === 0) {
    throw new Error(`All batches failed: ${result.failed.map(f => f.error).join(", ")}`);
  }

  // Convert back to the legacy JSON string format
  const output = {
    folder_name: result.folder_name,
    documents: result.completed,
  };

  return JSON.stringify(output);
}

// Simplified test mode that generates only 1 document
const TEST_SYSTEM_PROMPT = `You are a strategic intelligence synthesis engine. Generate ONE Company Intelligence packet for a target company.

Do NOT include metadata headers (packet_type, company_name, etc.). Start directly with numbered sections.

OUTPUT:
Generate the Company Intelligence packet, then output a JSON object:
{
  "folder_name": "<Company Name>",
  "documents": [
    {"file_name": "01 - Company Intelligence - <Company Name>", "content": "..."}
  ]
}`;

export async function generateTestDocument(
  prospect: ProspectInput,
  onProgress?: ProgressCallback
): Promise<string> {
  const model = process.env.ANTHROPIC_MODEL || "claude-sonnet-4-20250514";

  console.log(`Generating test document for ${prospect.name} using ${model}...`);
  onProgress?.({ type: "progress", message: "Starting test generation...", progress: 10 });

  let fullText = "";

  const stream = client.messages.stream({
    model,
    max_tokens: 8000,
    messages: [
      {
        role: "user",
        content: `Generate ONE Company Intelligence packet for:\n\nCompany: ${prospect.name}\nDomain: ${prospect.domain}\n\nOutput the packet then the JSON.`,
      },
    ],
    system: TEST_SYSTEM_PROMPT,
  });

  for await (const event of stream) {
    if (
      event.type === "content_block_delta" &&
      event.delta.type === "text_delta"
    ) {
      fullText += event.delta.text;
    }
  }

  onProgress?.({ type: "progress", message: "Parsing response...", progress: 80 });

  if (!fullText) {
    throw new Error("No text response from Anthropic");
  }

  return fullText;
}
