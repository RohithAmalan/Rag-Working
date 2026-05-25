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
    const authenticated = await keycloak.init({
      onLoad: "check-sso",
      silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      pkceMethod: "S256",
      checkLoginIframe: false,
    });

    if (authenticated) {
      // Store Keycloak token so the existing api.js interceptor picks it up
      localStorage.setItem("access_token", keycloak.token);
      localStorage.setItem("username", keycloak.tokenParsed?.preferred_username || "");

      // Auto-refresh token 60 seconds before expiry
      keycloak.onTokenExpired = () => {
        keycloak
          .updateToken(60)
          .then(() => {
            localStorage.setItem("access_token", keycloak.token);
          })
          .catch(() => {
            localStorage.removeItem("access_token");
            localStorage.removeItem("username");
          });
      };
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

