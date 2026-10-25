import { useCallback, useEffect, useState } from "react";
import api, { errMsg } from "../api";
import { Alert, Empty, Spinner } from "../components";

const STATUSES = ["Saved", "Applied", "Interview", "Rejected", "Offer"];

function Row({ app, onChange, onDelete }) {
  const [notes, setNotes] = useState(app.notes);
  useEffect(() => setNotes(app.notes), [app.notes]);
  return (
    <div className="card app">
      <div className="row">
        <div>
          <h3>{app.job_title}</h3>
          <p className="muted">{app.company}{app.applied_date ? ` · Applied ${app.applied_date}` : ""}</p>
        </div>
        <select aria-label={`Status for ${app.job_title}`} value={app.status} onChange={(e) => onChange(app.id, { status: e.target.value })}>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>
      <label className="sr" htmlFor={`n${app.id}`}>Notes</label>
      <textarea id={`n${app.id}`} placeholder="Notes..." maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} />
      <div className="row">
        <button className="btn small" disabled={notes === app.notes} onClick={() => onChange(app.id, { notes })}>Save notes</button>
        <button className="btn small danger" onClick={() => onDelete(app.id)}>Remove</button>
      </div>
    </div>
  );
}

export default function Tracker() {
  const [apps, setApps] = useState(null);
  const [filters, setFilters] = useState({ q: "", status: "", sort: "newest" });
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    api.get("/applications", { params: filters }).then((r) => setApps(r.data)).catch((e) => setError(errMsg(e)));
  }, [filters]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  const change = async (id, body) => {
    setError(""); setMsg("");
    try { await api.patch(`/applications/${id}`, body); setMsg("Updated."); load(); } catch (e) { setError(errMsg(e)); }
  };
  const remove = async (id) => {
    if (!window.confirm("Remove this application?")) return;
    try { await api.delete(`/applications/${id}`); setMsg("Removed."); load(); } catch (e) { setError(errMsg(e)); }
  };
  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });

  return (
    <>
      <h1>Saved Jobs &amp; Applications</h1>
      <p className="muted">"Saved" means you bookmarked a job. Change the status to "Applied" only after you really apply. Notes are optional.</p>
      {apps && (
        <div className="stats">
          {STATUSES.map((s) => <span key={s} className="chip">{s}: {apps.filter((a) => a.status === s).length}</span>)}
        </div>
      )}
      <div className="card filters">
        <input aria-label="Search applications" placeholder="Search..." value={filters.q} onChange={set("q")} />
        <select aria-label="Filter by status" value={filters.status} onChange={set("status")}>
          <option value="">All statuses</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select aria-label="Sort" value={filters.sort} onChange={set("sort")}>
          <option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="company">Company A–Z</option>
        </select>
      </div>
      <Alert>{error}</Alert>
      <Alert type="success">{msg}</Alert>
      {!apps && !error && <Spinner />}
      {apps && !apps.length && <Empty>Nothing saved yet. Open a job and press "Save job".</Empty>}
      {apps?.map((a) => <Row key={a.id} app={a} onChange={change} onDelete={remove} />)}
    </>
  );
}
