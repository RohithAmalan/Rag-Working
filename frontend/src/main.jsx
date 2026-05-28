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
      // Extract user info from Keycloak token
      const username = keycloak.tokenParsed?.preferred_username || "";
      const email = keycloak.tokenParsed?.email || "";
      const roles = keycloak.tokenParsed?.realm_access?.roles || [];
      
      // Store Keycloak token so the existing api.js interceptor picks it up
      localStorage.setItem("access_token", keycloak.token);
      localStorage.setItem("username", username);
      localStorage.setItem("user_roles", JSON.stringify(roles));
      
      // Store complete user object for useAuth hook
      localStorage.setItem('user', JSON.stringify({
        username: username,
        roles: roles,
        email: email
      }));

      // Auto-refresh token 60 seconds before expiry
      keycloak.onTokenExpired = () => {
        keycloak
          .updateToken(60)
          .then(() => {
            localStorage.setItem("access_token", keycloak.token);
            // Update user object with refreshed token
            const refreshedRoles = keycloak.tokenParsed?.realm_access?.roles || [];
            localStorage.setItem('user', JSON.stringify({
              username: keycloak.tokenParsed?.preferred_username || username,
              roles: refreshedRoles,
              email: keycloak.tokenParsed?.email || email
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

