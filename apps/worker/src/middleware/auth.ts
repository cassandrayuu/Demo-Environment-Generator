/**
 * Cloudflare Access JWT verification middleware
 */

import type { Env, CFAccessJWTPayload } from "../types";

// Cache for CF Access public keys
let cachedKeys: JsonWebKey[] | null = null;
let cachedKeysExpiry = 0;

/**
 * Fetch Cloudflare Access public keys
 */
async function fetchAccessKeys(teamDomain: string): Promise<JsonWebKey[]> {
  const now = Date.now();

  // Return cached keys if still valid (cache for 1 hour)
  if (cachedKeys && now < cachedKeysExpiry) {
    return cachedKeys;
  }

  const certsUrl = `https://${teamDomain}/cdn-cgi/access/certs`;
  const response = await fetch(certsUrl);

  if (!response.ok) {
    throw new Error(`Failed to fetch CF Access certs: ${response.status}`);
  }

  const data = (await response.json()) as { keys: JsonWebKey[] };
  cachedKeys = data.keys;
  cachedKeysExpiry = now + 60 * 60 * 1000; // 1 hour

  return cachedKeys;
}

/**
 * Decode a base64url string
 */
function base64UrlDecode(str: string): Uint8Array {
  // Add padding if needed
  const padded = str + "===".slice(0, (4 - (str.length % 4)) % 4);
  const base64 = padded.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Verify a CF Access JWT token
 */
async function verifyToken(
  token: string,
  teamDomain: string
): Promise<CFAccessJWTPayload> {
  const parts = token.split(".");
  if (parts.length !== 3) {
    throw new Error("Invalid JWT format");
  }

  const [headerB64, payloadB64, signatureB64] = parts;

  // Decode header to get key ID
  const headerJson = new TextDecoder().decode(base64UrlDecode(headerB64));
  const header = JSON.parse(headerJson) as { alg: string; kid: string };

  if (header.alg !== "RS256") {
    throw new Error(`Unsupported algorithm: ${header.alg}`);
  }

  // Fetch public keys
  const keys = await fetchAccessKeys(teamDomain);

  // Find the key with matching kid
  const key = keys.find((k) => k.kid === header.kid);
  if (!key) {
    throw new Error("Key not found");
  }

  // Import the public key
  const cryptoKey = await crypto.subtle.importKey(
    "jwk",
    key,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"]
  );

  // Verify signature
  const data = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  const signature = base64UrlDecode(signatureB64);

  const valid = await crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    cryptoKey,
    signature,
    data
  );

  if (!valid) {
    throw new Error("Invalid signature");
  }

  // Decode and return payload
  const payloadJson = new TextDecoder().decode(base64UrlDecode(payloadB64));
  const payload = JSON.parse(payloadJson) as CFAccessJWTPayload;

  // Check expiration
  if (payload.exp && payload.exp < Date.now() / 1000) {
    throw new Error("Token expired");
  }

  return payload;
}

/**
 * Authentication result
 */
export interface AuthResult {
  authenticated: boolean;
  userEmail?: string;
  error?: string;
}

/**
 * Verify CF Access authentication
 */
export async function verifyAccess(
  request: Request,
  env: Env
): Promise<AuthResult> {
  // Skip auth in development
  if (env.ENVIRONMENT === "development" && !env.CF_ACCESS_TEAM_DOMAIN) {
    return {
      authenticated: true,
      userEmail: "dev@localhost",
    };
  }

  // Check for CF Access JWT
  const cfAccessJwt =
    request.headers.get("CF-Access-JWT-Assertion") ||
    request.headers.get("Cf-Access-Jwt-Assertion");

  if (!cfAccessJwt) {
    return {
      authenticated: false,
      error: "Missing CF-Access-JWT-Assertion header",
    };
  }

  if (!env.CF_ACCESS_TEAM_DOMAIN) {
    return {
      authenticated: false,
      error: "CF_ACCESS_TEAM_DOMAIN not configured",
    };
  }

  try {
    const payload = await verifyToken(cfAccessJwt, env.CF_ACCESS_TEAM_DOMAIN);

    return {
      authenticated: true,
      userEmail: payload.email,
    };
  } catch (error) {
    return {
      authenticated: false,
      error: error instanceof Error ? error.message : "Token verification failed",
    };
  }
}

/**
 * Create an unauthorized response
 */
export function unauthorizedResponse(message: string): Response {
  return new Response(JSON.stringify({ error: message }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
}
