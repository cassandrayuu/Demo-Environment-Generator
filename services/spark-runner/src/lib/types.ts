export interface GeneratedDocument {
  file_name: string;
  content: string;
}

export interface GenerationResult {
  folder_name: string;
  documents: GeneratedDocument[];
}

export interface ParallelGenerationResult {
  folder_name: string;
  completed: GeneratedDocument[];
  failed: { batch: string; error: string }[];
}

export interface ProspectInput {
  name: string;
  domain: string;
}

export interface UploadResult {
  folderUrl: string;
  docUrls: { name: string; url: string }[];
}
