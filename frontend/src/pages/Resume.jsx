import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errMsg } from "../api";
import { Alert, Skills, Spinner } from "../components";

export default function Resume() {
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [warn, setWarn] = useState("");
  const [editing, setEditing] = useState(false);
  const [picked, setPicked] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/resume").then((r) => setResume(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setError(""); setOk(""); setWarn("");
    // Quick friendly checks only. The server validates the real file content and is the source of truth.
    if (file.size > 2 * 1024 * 1024) return setError("File is too large (max 2 MB).");
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    try {
      const { data } = await api.post("/resume", body);
      setResume(data);
      if (data.validation?.status === "possible") setOk(""), setWarn(data.validation.message);
      else setOk("Resume analyzed!");
    }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); e.target.value = ""; }
  };

  const startEdit = () => { setPicked(resume.skills); setEditing(true); setOk(""); setError(""); };
  const toggle = (name) => setPicked((p) => (p.includes(name) ? p.filter((x) => x !== name) : [...p, name]));
  const saveSkills = async (skills) => {
    setSaving(true); setError(""); setOk("");
    try {
      const { data } = await api.put("/resume/skills", { skills });
      setResume(data); setEditing(false); setOk("Skills updated. Job matches now use this list.");
    } catch (err) { setError(errMsg(err)); }
    finally { setSaving(false); }
  };

  if (loading) return <Spinner />;
  return (
    <>
      <h1>My Resume</h1>
      <div className="card">
        <label htmlFor="file" className="btn">{busy ? "Analyzing..." : resume ? "Upload a new PDF" : "Upload PDF resume"}</label>
        <input id="file" type="file" accept="application/pdf" onChange={upload} disabled={busy} hidden />
        <p className="muted">Text-based PDF only, max 2 MB and 10 pages. Scanned (image) PDFs, images and Word files are not supported yet. We check that the file looks like a resume, but we cannot verify that its contents are true.</p>
        <Alert>{error}</Alert>
        <Alert type="success">{ok}</Alert>
        <Alert type="info">{warn}</Alert>
      </div>
      {resume ? (
        <div className="card">
          <h2>{resume.skills.length} skills · {resume.filename}</h2>
          {editing ? (
            <>
              <p className="muted">Tick the skills you really have. Only skills from our list can be chosen.</p>
              <div className="picker">
                {resume.available_skills.map((n) => (
                  <label key={n} className={`pick ${picked.includes(n) ? "on" : ""}`}>
                    <input type="checkbox" checked={picked.includes(n)} onChange={() => toggle(n)} /> {n}
                  </label>
                ))}
              </div>
              <div className="row">
                <button className="btn" disabled={saving} onClick={() => saveSkills(picked)}>{saving ? "Saving..." : "Save skills"}</button>
                <button className="btn ghost" disabled={saving} onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </>
          ) : (
            <>
              {resume.skills.length ? <Skills list={resume.skills} /> : <p>No skills selected or detected.</p>}
              <div className="row">
                <button className="btn ghost small" onClick={startEdit}>Edit skills</button>
                {resume.skills_edited && <button className="btn ghost small" disabled={saving} onClick={() => saveSkills(resume.detected_skills)}>Reset to detected</button>}
              </div>
              {resume.skills_edited && <p className="muted">You edited this list by hand.</p>}
            </>
          )}
          <p className="muted">Skills are found by keyword matching against a fixed dictionary, so skills outside the dictionary are not detected. Skill detection is rule-based, not AI; optional AI tips are on each job page.</p>
          {!editing && <p><Link className="btn" to="/jobs">See matching jobs</Link></p>}
        </div>
      ) : <div className="empty">No resume yet. Upload one to see your skills.</div>}
    </>
  );
}
