import type { OAuth2Client } from "google-auth-library";
import type { GoogleAuth } from "googleapis-common";

export type AuthClient = OAuth2Client | GoogleAuth;

export interface AuthProvider {
  getClient(): Promise<AuthClient>;
  getType(): "oauth" | "service-account";
}
