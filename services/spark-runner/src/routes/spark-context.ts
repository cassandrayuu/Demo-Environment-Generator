import { Router, Request, Response } from "express";
import { generateDocuments, generateTestDocument } from "../lib/anthropic.js";
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

  try {
    // Step 1: Generate documents via Anthropic
    sendSSE(res, "progress", {
      step: "generating",
      message: testMode ? "Generating test document..." : "Generating strategic intelligence...",
      progress: 5,
    });

    const generateFn = testMode ? generateTestDocument : generateDocuments;
    const rawOutput = await generateFn(prospect, (event) => {
      if (event.type === "progress") {
        sendSSE(res, "progress", {
          step: "generating",
          message: event.message,
          progress: event.progress,
        });
      }
    });

    // Step 2: Parse the response
    sendSSE(res, "progress", {
      step: "parsing",
      message: "Parsing response...",
      progress: 80,
    });

    let result: GenerationResult;
    try {
      result = parseGenerationResult(rawOutput);
    } catch (parseError) {
      console.error("Parse error:", parseError);
      sendSSE(res, "error", {
        message: `Failed to parse response: ${parseError instanceof Error ? parseError.message : parseError}`,
      });
      return res.end();
    }

    console.log(`Parsed ${result.documents.length} documents`);

    // Step 3: Upload to Google Drive
    sendSSE(res, "progress", {
      step: "uploading",
      message: `Creating folder: ${result.folder_name}`,
      progress: 85,
    });

    const uploadResult = await uploadDocuments(
      result.folder_name,
      result.documents,
      (event) => {
        sendSSE(res, "progress", {
          step: "uploading",
          document: event.document,
          total: event.total,
          name: event.name,
        });
      }
    );

    // Step 4: Complete
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`[${new Date().toISOString()}] SUCCESS | ${prospect.name} (${prospect.domain}) | ${result.documents.length} docs | ${duration}s`);

    sendSSE(res, "complete", {
      folder_name: result.folder_name,
      folder_url: uploadResult.folderUrl,
      documents: uploadResult.docUrls,
    });

  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[${new Date().toISOString()}] FAILED | ${prospect.name} (${prospect.domain}) | ${duration}s | ${errorMessage}`);

    sendSSE(res, "error", {
      message: errorMessage,
    });
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
