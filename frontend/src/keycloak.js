/**
 * Keycloak instance configuration.
 *
 * Environment variables (set in .env or vite.config.js):
 *   VITE_KEYCLOAK_URL       — Keycloak server URL  (default: http://localhost:8080)
 *   VITE_KEYCLOAK_REALM     — Realm name            (default: rag-realm)
 *   VITE_KEYCLOAK_CLIENT_ID — Public client ID      (default: rag-app)
 */

import Keycloak from "keycloak-js";

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8080",
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "rag-realm",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "rag-app",
});

export default keycloak;
