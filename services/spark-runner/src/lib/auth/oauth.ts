import { google } from "googleapis";
import type { OAuth2Client } from "google-auth-library";
import type { AuthProvider, AuthClient } from "./types.js";

const SCOPES = [
  "https://www.googleapis.com/auth/drive",
  "https://www.googleapis.com/auth/documents",
];

interface OAuthCredentials {
  client_id: string;
  client_secret: string;
  redirect_uris?: string[];
}

interface OAuthTokens {
  access_token?: string;
  refresh_token: string;
  expiry_date?: number;
}

export class OAuthAuthProvider implements AuthProvider {
  private client: OAuth2Client | null = null;

  getType(): "oauth" {
    return "oauth";
  }

  async getClient(): Promise<AuthClient> {
    if (this.client) {
      return this.client;
    }

    // Parse OAuth credentials
    const credentialsStr = process.env.GOOGLE_OAUTH_CREDENTIALS_JSON;
    if (!credentialsStr) {
      throw new Error("GOOGLE_OAUTH_CREDENTIALS_JSON environment variable not set");
    }

    let credentials: { installed?: OAuthCredentials; web?: OAuthCredentials };
    try {
      credentials = JSON.parse(credentialsStr);
    } catch (e) {
      throw new Error(`Failed to parse GOOGLE_OAUTH_CREDENTIALS_JSON: ${e instanceof Error ? e.message : e}`);
    }

    const oauthConfig = credentials.installed || credentials.web;
    if (!oauthConfig) {
      throw new Error("Invalid OAuth credentials format: missing 'installed' or 'web' key");
    }

    // Parse refresh token
    const refreshToken = process.env.GOOGLE_OAUTH_REFRESH_TOKEN;
    if (!refreshToken) {
      throw new Error("GOOGLE_OAUTH_REFRESH_TOKEN environment variable not set");
    }

    // Create OAuth2 client
    const redirectUri = oauthConfig.redirect_uris?.[0] || "http://localhost:3000/oauth/callback";
    this.client = new google.auth.OAuth2(
      oauthConfig.client_id,
      oauthConfig.client_secret,
      redirectUri
    );

    // Set credentials with refresh token
    this.client.setCredentials({
      refresh_token: refreshToken,
    });

    // Verify the token works by getting an access token
    try {
      await this.client.getAccessToken();
    } catch (e) {
      throw new Error(`Failed to refresh OAuth token: ${e instanceof Error ? e.message : e}`);
    }

    return this.client;
  }

  /**
   * Generate the authorization URL for one-time setup
   */
  static getAuthUrl(credentials: OAuthCredentials): string {
    const redirectUri = credentials.redirect_uris?.[0] || "http://localhost:3000/oauth/callback";
    const client = new google.auth.OAuth2(
      credentials.client_id,
      credentials.client_secret,
      redirectUri
    );

    return client.generateAuthUrl({
      access_type: "offline",
      scope: SCOPES,
      prompt: "consent", // Force consent to get refresh token
    });
  }

  /**
   * Exchange authorization code for tokens (used by setup script)
   */
  static async exchangeCode(
    credentials: OAuthCredentials,
    code: string
  ): Promise<OAuthTokens> {
    const redirectUri = credentials.redirect_uris?.[0] || "http://localhost:3000/oauth/callback";
    const client = new google.auth.OAuth2(
      credentials.client_id,
      credentials.client_secret,
      redirectUri
    );

    const { tokens } = await client.getToken(code);
    if (!tokens.refresh_token) {
      throw new Error("No refresh token received. Make sure to revoke previous access and try again.");
    }

    return {
      access_token: tokens.access_token || undefined,
      refresh_token: tokens.refresh_token,
      expiry_date: tokens.expiry_date || undefined,
    };
  }
}
