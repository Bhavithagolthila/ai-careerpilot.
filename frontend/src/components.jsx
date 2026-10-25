import { Link, NavLink, Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function Navbar() {
  const { user, logout } = useAuth();
  return (
    <header className="nav">
      <Link to="/" className="brand">AI CareerPilot</Link>
      <nav aria-label="Main">
        {user ? (
          <>
            <NavLink to="/resume">Resume</NavLink>
            <NavLink to="/jobs">Jobs</NavLink>
            <NavLink to="/tracker">Tracker</NavLink>
            <button className="btn ghost" onClick={logout}>Logout</button>
          </>
        ) : (
          <>
            <NavLink to="/login">Login</NavLink>
            <Link to="/register" className="btn">Sign up</Link>
          </>
        )}
      </nav>
    </header>
  );
}

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  return user ? children : <Navigate to="/login" replace />;
}

export const Spinner = () => <p className="muted" role="status">Loading...</p>;
export const Alert = ({ type = "error", children }) =>
  children ? <p className={`alert ${type}`} role={type === "error" ? "alert" : "status"}>{children}</p> : null;
export const Empty = ({ children }) => <div className="empty">{children}</div>;

export const Skills = ({ list, kind = "" }) => (
  <div className="chips">{list.map((s) => <span key={s} className={`chip ${kind}`}>{s}</span>)}</div>
);

export function MatchBar({ percent }) {
  const tone = percent >= 70 ? "good" : percent >= 40 ? "mid" : "low";
  return (
    <div className="match" aria-label={`${percent}% match`}>
      <div className="bar"><div className={`fill ${tone}`} style={{ width: `${percent}%` }} /></div>
      <strong>{percent}%</strong>
    </div>
  );
}

export const Badge = ({ kind = "", children }) => <span className={`badge ${kind}`}>{children}</span>;

export const DemoNotice = () => (
  <Alert type="info">
    These are <strong>sample jobs for demonstration</strong>, not real vacancies. Companies and details are made up and there are no application links.
  </Alert>
);
