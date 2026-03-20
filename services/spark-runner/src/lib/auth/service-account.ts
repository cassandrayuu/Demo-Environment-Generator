import { google } from "googleapis";
import { GoogleAuth } from "google-auth-library";
import type { AuthProvider, AuthClient } from "./types.js";

const SCOPES = [
  "https://www.googleapis.com/auth/drive",
  "https://www.googleapis.com/auth/documents",
];

export class ServiceAccountAuthProvider implements AuthProvider {
  private auth: GoogleAuth | null = null;

  getType(): "service-account" {
    return "service-account";
  }

  async getClient(): Promise<AuthClient> {
    if (this.auth) {
      return this.auth;
    }

    const jsonStr = process.env.GOOGLE_SERVICE_ACCOUNT_JSON;
    if (!jsonStr) {
      throw new Error("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set");
    }

    let credentials: Record<string, unknown>;
    try {
      credentials = JSON.parse(jsonStr);
    } catch (e) {
      throw new Error(`Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: ${e instanceof Error ? e.message : e}`);
    }

    this.auth = new google.auth.GoogleAuth({
      credentials,
      scopes: SCOPES,
    });

    return this.auth;
  }
}
