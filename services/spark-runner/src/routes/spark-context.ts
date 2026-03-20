import { Router, Request, Response } from "express";
import { generateDocumentsParallel, generateTestDocument } from "../lib/anthropic.js";
import { parseGenerationResult } from "../lib/parse.js";
import { uploadDocuments } from "../lib/google-drive.js";
import type { ProspectInput, GenerationResult } from "../lib/types.js";

export const sparkContextRouter = Router();

interface SparkContextRequest {
  prospect_name: string;
  domain: string;
  test_mode?: boolean;
}

function sendSSE(res: Response, event: string, data: Record<string, unknown>) {
  res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

/**
 * Start a keepalive interval that sends ping events every 15 seconds
 * to prevent proxy/load balancer timeouts on long-running SSE connections
 */
function startKeepalive(res: Response): NodeJS.Timeout {
  return setInterval(() => {
    // SSE comment line - keeps connection alive without triggering event handlers
    res.write(": keepalive\n\n");
  }, 15000);
}

sparkContextRouter.post("/spark-context", async (req: Request, res: Response) => {
  const body = req.body as SparkContextRequest;

  // Validate input
  if (!body.prospect_name || !body.domain) {
    return res.status(400).json({ error: "Missing required fields: prospect_name, domain" });
  }

  const prospect: ProspectInput = {
    name: body.prospect_name,
    domain: body.domain,
  };

  const testMode = body.test_mode === true;

  // Set up SSE
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");

  const startTime = Date.now();
  console.log(`[${new Date().toISOString()}] Starting generation for ${prospect.name} (${prospect.domain})`);

  // Start keepalive pings to prevent connection timeout
  const keepaliveInterval = startKeepalive(res);

  try {
    // Test mode uses the simple single-doc generator
    if (testMode) {
      sendSSE(res, "progress", {
        step: "generating",
        message: "Generating test document...",
        progress: 5,
      });

      const rawOutput = await generateTestDocument(prospect, (event) => {
        if (event.type === "progress") {
          sendSSE(res, "progress", {
            step: "generating",
            message: event.message,
            progress: event.progress,
          });
        }
      });

      // Parse and upload test document
      sendSSE(res, "progress", { step: "parsing", message: "Parsing response...", progress: 80 });
      const result = parseGenerationResult(rawOutput);

      sendSSE(res, "progress", { step: "uploading", message: `Creating folder: ${result.folder_name}`, progress: 85 });
      const uploadResult = await uploadDocuments(result.folder_name, result.documents);

      const duration = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`[${new Date().toISOString()}] SUCCESS (test) | ${prospect.name} | ${result.documents.length} docs | ${duration}s`);

      sendSSE(res, "complete", {
        folder_name: result.folder_name,
        folder_url: uploadResult.folderUrl,
        documents: uploadResult.docUrls,
      });

      return res.end();
    }

    // Production mode: parallel batch generation
    sendSSE(res, "progress", {
      step: "generating",
      message: "Generating strategic intelligence (parallel mode)...",
      progress: 5,
    });

    // Track batch progress
    let completedBatches = 0;
    const totalBatches = 4;

    const parallelResult = await generateDocumentsParallel(prospect, (event) => {
      if (event.type === "batch_start") {
        sendSSE(res, "progress", {
          step: "generating",
          message: event.message,
          progress: 10 + (completedBatches / totalBatches) * 60,
          batch: event.batch,
        });
      } else if (event.type === "batch_complete") {
        completedBatches++;
        sendSSE(res, "progress", {
          step: "generating",
          message: event.message,
          progress: 10 + (completedBatches / totalBatches) * 60,
          batch: event.batch,
        });
      } else if (event.type === "batch_retry") {
        sendSSE(res, "progress", {
          step: "generating",
          message: event.message,
          progress: 10 + (completedBatches / totalBatches) * 60,
          batch: event.batch,
        });
      } else if (event.type === "progress") {
        sendSSE(res, "progress", {
          step: "generating",
          message: event.message,
          progress: event.progress,
        });
      }
    });

    // Check if we have any documents to upload
    if (parallelResult.completed.length === 0) {
      const errors = parallelResult.failed.map(f => `${f.batch}: ${f.error}`).join("; ");
      throw new Error(`All batches failed: ${errors}`);
    }

    // Log partial failures (if any)
    if (parallelResult.failed.length > 0) {
      console.warn(`[${new Date().toISOString()}] Partial failure | ${prospect.name} | Failed batches: ${parallelResult.failed.map(f => f.batch).join(", ")}`);
    }

    console.log(`Generated ${parallelResult.completed.length} documents`);

    // Upload to Google Drive
    sendSSE(res, "progress", {
      step: "uploading",
      message: `Creating folder: ${parallelResult.folder_name}`,
      progress: 85,
    });

    const uploadResult = await uploadDocuments(
      parallelResult.folder_name,
      parallelResult.completed,
      (event) => {
        sendSSE(res, "progress", {
          step: "uploading",
          document: event.document,
          total: event.total,
          name: event.name,
        });
      }
    );

    // Complete
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`[${new Date().toISOString()}] SUCCESS | ${prospect.name} (${prospect.domain}) | ${parallelResult.completed.length} docs | ${duration}s`);

    sendSSE(res, "complete", {
      folder_name: parallelResult.folder_name,
      folder_url: uploadResult.folderUrl,
      documents: uploadResult.docUrls,
      // Include failed batches info for transparency
      failed_batches: parallelResult.failed.length > 0 ? parallelResult.failed : undefined,
    });

  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[${new Date().toISOString()}] FAILED | ${prospect.name} (${prospect.domain}) | ${duration}s | ${errorMessage}`);

    sendSSE(res, "error", {
      message: errorMessage,
    });
  } finally {
    // Always clear keepalive interval
    clearInterval(keepaliveInterval);
  }

  res.end();
});

// Smoke test endpoint - just tests Google Drive connectivity
sparkContextRouter.post("/spark-context/smoke", async (req: Request, res: Response) => {
  const body = req.body as { folder_name?: string };
  const folderName = body.folder_name || "Smoke Test";

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");

  try {
    sendSSE(res, "progress", {
      step: "uploading",
      message: "Testing Google Drive connection...",
      progress: 50,
    });

    const testDocs = [
      {
        file_name: "Smoke Test Document",
        content: "This is a smoke test document to validate Google Drive integration.\n\nIf you see this, the Drive + Docs APIs are working correctly.",
      },
    ];

    const uploadResult = await uploadDocuments(folderName, testDocs);

    sendSSE(res, "complete", {
      folder_name: folderName,
      folder_url: uploadResult.folderUrl,
      documents: uploadResult.docUrls,
    });
  } catch (error) {
    sendSSE(res, "error", {
      message: error instanceof Error ? error.message : String(error),
    });
  }

  res.end();
});
