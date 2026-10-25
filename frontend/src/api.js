import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000" });

// Attach the JWT to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Expired/invalid token on a protected call: clear it and go to login (not for the login call itself).
api.interceptors.response.use((r) => r, (e) => {
  const url = e.config?.url || "";
  if (e.response?.status === 401 && !url.includes("/auth/login") && localStorage.getItem("token")) {
    localStorage.removeItem("token");
    window.location.assign("/login");
  }
  return Promise.reject(e);
});

// Turn any backend error into a readable message.
export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (!e.response) return "Cannot reach the server. Is the backend running?";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => `${x.loc?.slice(-1)[0]}: ${x.msg}`).join(". ");
  return "Something went wrong. Please try again.";
}

export default api;
