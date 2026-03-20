import type { AuthProvider } from "./types.js";
import { OAuthAuthProvider } from "./oauth.js";
import { ServiceAccountAuthProvider } from "./service-account.js";

export type { AuthProvider, AuthClient } from "./types.js";
export { OAuthAuthProvider } from "./oauth.js";
export { ServiceAccountAuthProvider } from "./service-account.js";

let cachedProvider: AuthProvider | null = null;

/**
 * Get the configured auth provider based on environment variables.
 *
 * Priority:
 * 1. If GOOGLE_OAUTH_CREDENTIALS_JSON and GOOGLE_OAUTH_REFRESH_TOKEN are set, use OAuth
 * 2. If GOOGLE_SERVICE_ACCOUNT_JSON is set, use Service Account
 * 3. Throw error if neither is configured
 */
export function getAuthProvider(): AuthProvider {
  if (cachedProvider) {
    return cachedProvider;
  }

  // Check for OAuth configuration
  const hasOAuth =
    process.env.GOOGLE_OAUTH_CREDENTIALS_JSON &&
    process.env.GOOGLE_OAUTH_REFRESH_TOKEN;

  // Check for Service Account configuration
  const hasServiceAccount = process.env.GOOGLE_SERVICE_ACCOUNT_JSON;

  if (hasOAuth) {
    console.log("Using OAuth authentication");
    cachedProvider = new OAuthAuthProvider();
  } else if (hasServiceAccount) {
    console.log("Using Service Account authentication");
    cachedProvider = new ServiceAccountAuthProvider();
  } else {
    throw new Error(
      "No Google authentication configured. Set either:\n" +
      "  - GOOGLE_OAUTH_CREDENTIALS_JSON + GOOGLE_OAUTH_REFRESH_TOKEN (for OAuth), or\n" +
      "  - GOOGLE_SERVICE_ACCOUNT_JSON (for Service Account)"
    );
  }

  return cachedProvider;
}

/**
 * Clear the cached provider (useful for testing)
 */
export function clearAuthProvider(): void {
  cachedProvider = null;
}
