import Anthropic from "@anthropic-ai/sdk";
import { SYSTEM_PROMPT, buildUserPrompt } from "./prompt.js";
import type { ProspectInput } from "./types.js";

const client = new Anthropic();

export interface ProgressCallback {
  (event: { type: string; message?: string; progress?: number }): void;
}

export async function generateDocuments(
  prospect: ProspectInput,
  onProgress?: ProgressCallback
): Promise<string> {
  const model = process.env.ANTHROPIC_MODEL || "claude-sonnet-4-20250514";

  console.log(`Generating packets for ${prospect.name} using ${model}...`);
  onProgress?.({ type: "progress", message: "Starting generation...", progress: 5 });

  let fullText = "";
  let lastProgressUpdate = 0;

  const stream = client.messages.stream({
    model,
    max_tokens: 64000,
    messages: [
      {
        role: "user",
        content: buildUserPrompt(prospect),
      },
    ],
    system: SYSTEM_PROMPT,
  });

  for await (const event of stream) {
    if (
      event.type === "content_block_delta" &&
      event.delta.type === "text_delta"
    ) {
      fullText += event.delta.text;

      // Update progress every ~5000 chars (roughly every few seconds)
      const currentLength = fullText.length;
      if (currentLength - lastProgressUpdate > 5000) {
        // Estimate progress based on expected output size (~150k chars)
        const estimatedProgress = Math.min(75, Math.floor((currentLength / 150000) * 70) + 10);
        onProgress?.({
          type: "progress",
          message: "Generating intelligence packets...",
          progress: estimatedProgress
        });
        lastProgressUpdate = currentLength;
      }
    }
  }

  console.log(`Generation complete. Output length: ${fullText.length} chars`);
  onProgress?.({ type: "progress", message: "Parsing response...", progress: 80 });

  if (!fullText) {
    throw new Error("No text response from Anthropic");
  }

  return fullText;
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
