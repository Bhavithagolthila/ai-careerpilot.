import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import api, { errMsg } from "../api";
import { useAuth } from "../AuthContext";
import { Alert } from "../components";

function Field({ label, id, ...props }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} required {...props} />
    </div>
  );
}

export function Register() {
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try { await api.post("/auth/register", f); nav("/login", { state: { registered: true } }); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  return (
    <form className="card form" onSubmit={submit}>
      <h2>Create your account</h2>
      <Alert>{error}</Alert>
      <Field label="Name" id="name" value={f.name} onChange={set("name")} minLength={2} autoComplete="name" />
      <Field label="Email" id="email" type="email" value={f.email} onChange={set("email")} autoComplete="email" />
      <Field label="Password (8+ characters)" id="password" type="password" value={f.password}
             onChange={set("password")} minLength={8} maxLength={72} autoComplete="new-password" />
      <button className="btn" disabled={busy}>{busy ? "Creating..." : "Sign up"}</button>
      <p className="muted">Already registered? <Link to="/login">Login</Link></p>
    </form>
  );
}

export function Login() {
  const [f, setF] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const nav = useNavigate();
  const registered = useLocation().state?.registered;

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try { await login(f.email, f.password); nav("/resume"); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  return (
    <form className="card form" onSubmit={submit}>
      <h2>Welcome back</h2>
      {registered && <Alert type="success">Account created. Please log in.</Alert>}
      <Alert>{error}</Alert>
      <Field label="Email" id="email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} autoComplete="email" />
      <Field label="Password" id="password" type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete="current-password" />
      <button className="btn" disabled={busy}>{busy ? "Signing in..." : "Login"}</button>
      <p className="muted">New here? <Link to="/register">Create an account</Link></p>
    </form>
  );
}
