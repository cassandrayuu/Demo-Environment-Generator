import { google } from "googleapis";
import type { GeneratedDocument, UploadResult } from "./types.js";
import { getAuthProvider } from "./auth/index.js";

function getTimestampSuffix(): string {
  const now = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

async function folderExists(
  drive: ReturnType<typeof google.drive>,
  folderName: string,
  parentFolderId: string
): Promise<boolean> {
  const response = await drive.files.list({
    q: `name='${folderName}' and '${parentFolderId}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false`,
    fields: "files(id)",
  });

  return (response.data.files?.length ?? 0) > 0;
}

export async function createFolder(folderName: string): Promise<{ id: string; name: string }> {
  const provider = getAuthProvider();
  const auth = await provider.getClient();
  const drive = google.drive({ version: "v3", auth: auth as any });
  const parentFolderId = process.env.GOOGLE_DRIVE_PARENT_FOLDER_ID;

  if (!parentFolderId) {
    throw new Error("GOOGLE_DRIVE_PARENT_FOLDER_ID environment variable not set");
  }

  // Check if folder with same name exists
  let finalName = folderName;
  if (await folderExists(drive, folderName, parentFolderId)) {
    finalName = `${folderName} - ${getTimestampSuffix()}`;
    console.log(`Folder "${folderName}" exists. Creating: ${finalName}`);
  }

  console.log(`Creating folder: ${finalName}`);

  const response = await drive.files.create({
    requestBody: {
      name: finalName,
      mimeType: "application/vnd.google-apps.folder",
      parents: [parentFolderId],
    },
    fields: "id, webViewLink",
  });

  if (!response.data.id) {
    throw new Error("Failed to create folder");
  }

  console.log(`Folder created: ${response.data.webViewLink}`);
  return { id: response.data.id, name: finalName };
}

export async function createDocument(
  folderId: string,
  doc: GeneratedDocument
): Promise<{ id: string; url: string }> {
  const provider = getAuthProvider();
  const auth = await provider.getClient();
  const drive = google.drive({ version: "v3", auth: auth as any });
  const docs = google.docs({ version: "v1", auth: auth as any });

  // Create empty Google Doc
  const fileResponse = await drive.files.create({
    requestBody: {
      name: doc.file_name,
      mimeType: "application/vnd.google-apps.document",
      parents: [folderId],
    },
    fields: "id, webViewLink",
  });

  const docId = fileResponse.data.id;
  const docUrl = fileResponse.data.webViewLink;
  if (!docId) {
    throw new Error(`Failed to create document: ${doc.file_name}`);
  }

  // Insert content into the document
  await docs.documents.batchUpdate({
    documentId: docId,
    requestBody: {
      requests: [
        {
          insertText: {
            location: { index: 1 },
            text: doc.content,
          },
        },
      ],
    },
  });

  console.log(`  Created: ${doc.file_name}`);
  return { id: docId, url: docUrl || `https://docs.google.com/document/d/${docId}` };
}

export interface UploadProgressCallback {
  (event: { document: number; total: number; name: string }): void;
}

export async function uploadDocuments(
  folderName: string,
  documents: GeneratedDocument[],
  onProgress?: UploadProgressCallback
): Promise<UploadResult> {
  const folder = await createFolder(folderName);

  console.log(`Uploading ${documents.length} documents...`);

  const docUrls: { name: string; url: string }[] = [];
  for (let i = 0; i < documents.length; i++) {
    const doc = documents[i];
    onProgress?.({ document: i + 1, total: documents.length, name: doc.file_name });
    const result = await createDocument(folder.id, doc);
    docUrls.push({ name: doc.file_name, url: result.url });
  }

  const folderUrl = `https://drive.google.com/drive/folders/${folder.id}`;
  return { folderUrl, docUrls };
}
