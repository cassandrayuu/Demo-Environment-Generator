#!/usr/bin/env npx tsx
/**
 * One-time OAuth Setup Script
 *
 * This script helps you obtain a refresh token for Google Drive/Docs access.
 * Run it once with your OAuth credentials to get a refresh token, then store
 * that token in your environment variables.
 *
 * Prerequisites:
 * 1. Create OAuth 2.0 credentials in Google Cloud Console:
 *    - Go to APIs & Services > Credentials
 *    - Create OAuth Client ID (Desktop app)
 *    - Download the JSON file
 *
 * Usage:
 *   npx tsx scripts/setup-oauth.ts path/to/oauth-credentials.json
 *
 * The script will:
 * 1. Open your browser for Google authorization
 * 2. Wait for you to authorize
 * 3. Print the refresh token to add to your .env file
 */

import { readFileSync } from "fs";
import { createServer } from "http";
import { google } from "googleapis";

const SCOPES = [
  "https://www.googleapis.com/auth/drive",
  "https://www.googleapis.com/auth/documents",
];

const PORT = 3000;
const REDIRECT_URI = `http://localhost:${PORT}/oauth/callback`;

interface OAuthCredentials {
  installed?: {
    client_id: string;
    client_secret: string;
    redirect_uris?: string[];
  };
  web?: {
    client_id: string;
    client_secret: string;
    redirect_uris?: string[];
  };
}

async function main() {
  const credentialsPath = process.argv[2];

  if (!credentialsPath) {
    console.error("Usage: npx tsx scripts/setup-oauth.ts <path-to-credentials.json>");
    console.error("");
    console.error("To get credentials:");
    console.error("1. Go to Google Cloud Console > APIs & Services > Credentials");
    console.error("2. Create OAuth Client ID (Desktop app type)");
    console.error("3. Download the JSON file");
    console.error("4. Run this script with the path to that file");
    process.exit(1);
  }

  // Read and parse credentials
  let credentials: OAuthCredentials;
  try {
    const content = readFileSync(credentialsPath, "utf-8");
    credentials = JSON.parse(content);
  } catch (e) {
    console.error(`Failed to read credentials file: ${e instanceof Error ? e.message : e}`);
    process.exit(1);
  }

  const config = credentials.installed || credentials.web;
  if (!config) {
    console.error("Invalid credentials file: missing 'installed' or 'web' key");
    process.exit(1);
  }

  // Create OAuth2 client
  const oauth2Client = new google.auth.OAuth2(
    config.client_id,
    config.client_secret,
    REDIRECT_URI
  );

  // Generate auth URL
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: "offline",
    scope: SCOPES,
    prompt: "consent", // Force consent to get refresh token
  });

  console.log("\n=== Google OAuth Setup ===\n");
  console.log("1. Opening your browser for authorization...\n");

  // Open browser
  const { exec } = await import("child_process");
  const platform = process.platform;
  const command = platform === "darwin" ? "open" : platform === "win32" ? "start" : "xdg-open";
  exec(`${command} "${authUrl}"`);

  console.log("   If the browser didn't open, visit this URL:\n");
  console.log(`   ${authUrl}\n`);
  console.log("2. Waiting for authorization...\n");

  // Start local server to receive callback
  const code = await new Promise<string>((resolve, reject) => {
    const server = createServer((req, res) => {
      const url = new URL(req.url || "", `http://localhost:${PORT}`);

      if (url.pathname === "/oauth/callback") {
        const code = url.searchParams.get("code");
        const error = url.searchParams.get("error");

        if (error) {
          res.writeHead(400, { "Content-Type": "text/html" });
          res.end(`<h1>Authorization Failed</h1><p>Error: ${error}</p>`);
          server.close();
          reject(new Error(`Authorization failed: ${error}`));
          return;
        }

        if (code) {
          res.writeHead(200, { "Content-Type": "text/html" });
          res.end(`
            <h1>Authorization Successful!</h1>
            <p>You can close this window and return to the terminal.</p>
          `);
          server.close();
          resolve(code);
        }
      }
    });

    server.listen(PORT, () => {
      console.log(`   Listening on http://localhost:${PORT}/oauth/callback\n`);
    });

    // Timeout after 5 minutes
    setTimeout(() => {
      server.close();
      reject(new Error("Authorization timed out (5 minutes)"));
    }, 5 * 60 * 1000);
  });

  console.log("3. Exchanging code for tokens...\n");

  // Exchange code for tokens
  const { tokens } = await oauth2Client.getToken(code);

  if (!tokens.refresh_token) {
    console.error("ERROR: No refresh token received!");
    console.error("This usually means you've already authorized this app.");
    console.error("To fix:");
    console.error("1. Go to https://myaccount.google.com/permissions");
    console.error("2. Remove access for this app");
    console.error("3. Run this script again");
    process.exit(1);
  }

  // Output the results
  console.log("=== SUCCESS! ===\n");
  console.log("Add these to your .env file:\n");
  console.log("---");

  // Format credentials as single-line JSON
  const credentialsJson = JSON.stringify(credentials);
  console.log(`GOOGLE_OAUTH_CREDENTIALS_JSON=${credentialsJson}`);
  console.log("");
  console.log(`GOOGLE_OAUTH_REFRESH_TOKEN=${tokens.refresh_token}`);

  console.log("---\n");
  console.log("Note: Keep these values secret! Do not commit them to git.\n");
}

main().catch((e) => {
  console.error("Error:", e.message);
  process.exit(1);
});
