import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import App from "./App";
import keycloak from "./keycloak";
import "./styles/index.css";
import { TOAST_CONFIG } from "./config/constants";

/**
 * Attempt a silent Keycloak SSO check.
 * If Keycloak is unreachable (dev without KC running) we fall back to
 * the existing username/password form seamlessly.
 */
async function initKeycloak() {
  try {
    // Detect whether we have returned from Keycloak with an auth response
    // (authorization code or error). When present, initialize with
    // `check-sso` so the adapter can process the callback and populate tokens.
    const urlParams = new URLSearchParams(window.location.search);
    const hasAuthResponse = urlParams.has("code") || urlParams.has("error");

    const initOptions = {
      onLoad: hasAuthResponse ? "check-sso" : "none",
      silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      pkceMethod: "S256",
      checkLoginIframe: false,
    };

    const authenticated = await keycloak.init(initOptions);

      if (authenticated) {
      // Extract user info from Keycloak token
      const username = keycloak.tokenParsed?.preferred_username || "";
      const email = keycloak.tokenParsed?.email || "";
      const roles = keycloak.tokenParsed?.realm_access?.roles || [];

      // Persist tokens and user info so App.jsx can detect auth state
      localStorage.setItem("access_token", keycloak.token);
      localStorage.setItem("username", username);
      localStorage.setItem("user_roles", JSON.stringify(roles));
      localStorage.setItem("user", JSON.stringify({ username, roles, email }));

      // Auto-refresh token 60 seconds before expiry
      keycloak.onTokenExpired = () => {
        keycloak
          .updateToken(60)
          .then(() => {
            const refreshedRoles = keycloak.tokenParsed?.realm_access?.roles || [];
            // Update stored token with the refreshed one
            localStorage.setItem("access_token", keycloak.token);
            localStorage.setItem("user", JSON.stringify({
              username: keycloak.tokenParsed?.preferred_username || username,
              roles: refreshedRoles,
              email: keycloak.tokenParsed?.email || email,
            }));
          })
          .catch(() => {
            localStorage.removeItem("access_token");
            localStorage.removeItem("username");
            localStorage.removeItem("user_roles");
            localStorage.removeItem("user");
          });
      };
    }
    // If we processed an auth response from Keycloak, remove query params
    // (clean URL) so the app doesn't try to re-process the response on reload.
    if (hasAuthResponse) {
      const cleanUrl = `${window.location.origin}${window.location.pathname}${window.location.hash}`;
      window.history.replaceState(null, document.title, cleanUrl);
    }
  } catch {
    // Keycloak not reachable — continue with legacy form-based login
    console.info("Keycloak not reachable, using legacy auth");
  }

  return keycloak;
}

initKeycloak().then((kc) => {
  ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <BrowserRouter>
        <App keycloak={kc} />
        <Toaster
          position={TOAST_CONFIG.position}
          toastOptions={{
            duration: TOAST_CONFIG.duration,
            style: TOAST_CONFIG.style,
            success: TOAST_CONFIG.success,
            error: TOAST_CONFIG.error,
          }}
        />
      </BrowserRouter>
    </React.StrictMode>
  );
});

