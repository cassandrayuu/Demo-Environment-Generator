import type { GenerationResult, GeneratedDocument } from "./types.js";

export function parseGenerationResult(rawOutput: string): GenerationResult {
  // Try to extract JSON from the response (handles markdown code blocks)
  let jsonString = rawOutput.trim();

  // Remove markdown code block if present
  const jsonMatch = jsonString.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (jsonMatch) {
    jsonString = jsonMatch[1].trim();
  }

  // Try to find JSON object boundaries
  const startIndex = jsonString.indexOf("{");
  const endIndex = jsonString.lastIndexOf("}");

  if (startIndex === -1 || endIndex === -1) {
    console.error("Raw output:", rawOutput);
    throw new Error("No JSON object found in response");
  }

  jsonString = jsonString.slice(startIndex, endIndex + 1);

  let parsed: unknown;
  try {
    parsed = JSON.parse(jsonString);
  } catch (e) {
    console.error("Failed to parse JSON. Raw output:");
    console.error(rawOutput);
    throw new Error(`JSON parse error: ${e instanceof Error ? e.message : e}`);
  }

  // Validate structure
  if (!isValidGenerationResult(parsed)) {
    console.error("Invalid structure. Parsed result:");
    console.error(JSON.stringify(parsed, null, 2));
    throw new Error("Response does not match expected structure");
  }

  return parsed;
}

function isValidGenerationResult(obj: unknown): obj is GenerationResult {
  if (typeof obj !== "object" || obj === null) {
    return false;
  }

  const result = obj as Record<string, unknown>;

  if (typeof result.folder_name !== "string") {
    return false;
  }

  if (!Array.isArray(result.documents)) {
    return false;
  }

  for (const doc of result.documents) {
    if (!isValidDocument(doc)) {
      return false;
    }
  }

  return result.documents.length > 0;
}

function isValidDocument(obj: unknown): obj is GeneratedDocument {
  if (typeof obj !== "object" || obj === null) {
    return false;
  }

  const doc = obj as Record<string, unknown>;

  return (
    typeof doc.file_name === "string" &&
    doc.file_name.length > 0 &&
    typeof doc.content === "string" &&
    doc.content.length > 0
  );
}
