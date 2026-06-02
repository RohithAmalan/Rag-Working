import { useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import keycloak from "../keycloak";
import { API_CONFIG, STORAGE_KEYS } from "../config/constants";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // --- Form-based login (calls backend /auth/login, which proxies to Keycloak ROPC) ---
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!username || !password) {
      toast.error("Please enter username and password");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_CONFIG.baseURL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed");
      }

      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
      localStorage.setItem(STORAGE_KEYS.USERNAME, data.username);
      // Store user roles for RBAC
      if (data.roles) {
        localStorage.setItem(STORAGE_KEYS.USER_ROLES, JSON.stringify(data.roles));
      }
      // Store complete user object for useAuth hook
      localStorage.setItem('user', JSON.stringify({
        username: data.username,
        roles: data.roles || [],
        email: data.email || ''
      }));
      // Keep refresh_token for future token rotation
      if (data.refresh_token) {
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
      }

      toast.success(data.message || "Login successful!");
      if (onLogin) onLogin(data);
      navigate("/");
    } catch (error) {
      toast.error(error.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  // --- Keycloak SSO redirect (Authorization Code + PKCE) ---
  const handleSSOLogin = async () => {
    try {
      // In case startup silent init failed, initialize on-demand before redirect.
      if (!keycloak.didInitialize) {
        await keycloak.init({
          onLoad: "check-sso",
          pkceMethod: "S256",
          checkLoginIframe: false,
          silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
        });
      }

      await keycloak.login({ redirectUri: `${window.location.origin}/login` });
    } catch (error) {
      console.error("Keycloak SSO login failed", error);
      toast.error("Could not start Keycloak login. Please try again.");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top_right,_#fff1df,_#dff8ff_40%,_#f4f4f5_75%)] p-4">
      <div className="w-full max-w-md">
        <div className="rounded-3xl border border-white/70 bg-white/90 p-8 shadow-xl">
          <div className="mb-8 text-center">
            <h1 className="font-display text-3xl font-bold text-ink">RAG System</h1>
            <p className="mt-2 text-sm text-ink/70">Sign in to continue</p>
          </div>

          {/* SSO Button */}
          <button
            type="button"
            onClick={handleSSOLogin}
            className="mb-6 flex w-full items-center justify-center gap-3 rounded-xl border-2 border-blue-600 bg-blue-50 px-4 py-3 text-sm font-bold text-blue-700 transition hover:bg-blue-100"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 1C5.925 1 1 5.925 1 12s4.925 11 11 11 11-4.925 11-11S18.075 1 12 1zm0 2c4.971 0 9 4.029 9 9s-4.029 9-9 9-9-4.029-9-9 4.029-9 9-9zm0 4a5 5 0 100 10A5 5 0 0012 7zm0 2a3 3 0 110 6 3 3 0 010-6z"/>
            </svg>
            Sign in with Keycloak SSO
          </button>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-ink/10" />
            </div>
            <div className="relative flex justify-center text-xs text-ink/40">
              <span className="bg-white px-3">or sign in with credentials</span>
            </div>
          </div>

          {/* Username / Password form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-ink/80">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-coral focus:ring-2 focus:ring-coral/20"
                placeholder="Enter username"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink/80">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-coral focus:ring-2 focus:ring-coral/20"
                placeholder="Enter password"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-coral px-4 py-3 text-sm font-bold text-white shadow-lg transition-all hover:bg-coral/90 hover:shadow-xl disabled:cursor-not-allowed disabled:bg-gray-400 disabled:shadow-none"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <div className="mt-6 rounded-xl bg-sky/10 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink/50">Demo Credentials</p>
            <div className="mt-2 space-y-1 text-sm text-ink/70">
              <p>• admin / admin123</p>
              <p>• demo / demo123</p>
              <p>• user / user123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
