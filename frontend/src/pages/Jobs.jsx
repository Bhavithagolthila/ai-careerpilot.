import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errMsg } from "../api";
import { Alert, Badge, DemoNotice, Empty, MatchBar, Skills, Spinner } from "../components";

export function Jobs() {
  const [filters, setFilters] = useState({ q: "", location: "", role: "", experience: "" });
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      api.get("/jobs", { params: filters }).then((r) => { setData(r.data); setError(""); })
        .catch((e) => setError(errMsg(e)));
    }, 250); // wait for the user to stop typing
    return () => clearTimeout(t);
  }, [filters]);

  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });
  return (
    <>
      <h1>Jobs</h1>
      {data?.jobs.some((j) => j.is_demo) && <DemoNotice />}
      {data && !data.has_resume && <Alert type="info">Upload your resume to see match percentages. <Link to="/resume">Upload now</Link></Alert>}
      <div className="card filters">
        <input aria-label="Search jobs" placeholder="Search title, company..." value={filters.q} onChange={set("q")} />
        <input aria-label="Location" placeholder="Location" value={filters.location} onChange={set("location")} />
        <select aria-label="Role" value={filters.role} onChange={set("role")}>
          <option value="">All roles</option>
          {["Backend", "Frontend", "Full Stack", "Data", "DevOps"].map((r) => <option key={r}>{r}</option>)}
        </select>
        <select aria-label="Experience" value={filters.experience} onChange={set("experience")}>
          <option value="">Any experience</option>
          {["Fresher", "Junior", "Mid"].map((r) => <option key={r}>{r}</option>)}
        </select>
      </div>
      <Alert>{error}</Alert>
      {!data && !error && <Spinner />}
      {data && <p className="muted" role="status">Showing {data.jobs.length} of {data.total} jobs</p>}
      {data && !data.jobs.length && <Empty>No jobs match these filters.</Empty>}
      <div className="grid two">
        {data?.jobs.map((j) => (
          <Link key={j.id} to={`/jobs/${j.id}`} className="card job">
            <h3>{j.title} {j.is_demo && <Badge>Demo</Badge>} {j.saved && <Badge kind="ok">Saved</Badge>}</h3>
            <p className="muted">{j.company} · {j.location} · {j.experience}</p>
            {j.match && <MatchBar percent={j.match.percent} />}
            <Skills list={j.skills} />
          </Link>
        ))}
      </div>
    </>
  );
}

function Advice({ jobId }) {
  const [advice, setAdvice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = async () => {
    setBusy(true); setError("");
    try { setAdvice((await api.post(`/jobs/${jobId}/advice`)).data); }
    catch (e) { setError(errMsg(e)); }
    finally { setBusy(false); }
  };
  return (
    <div className="card">
      <h2>How to improve your chances</h2>
      {!advice && <button className="btn" onClick={load} disabled={busy}>{busy ? "Thinking..." : "Get tips"}</button>}
      <Alert>{error}</Alert>
      {advice && (
        <>
          <ul>{advice.tips.map((t) => <li key={t}>{t}</li>)}</ul>
          <p className="muted">{advice.source === "ai" ? "Written by an AI model from your skill list only (your resume text is never sent)." : "Rule-based tips based on your missing skills."}</p>
        </>
      )}
    </div>
  );
}

export function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.get(`/jobs/${id}`).then((r) => setJob(r.data)).catch((e) => setError(errMsg(e)));
  }, [id]);

  const save = async () => {
    setMsg(""); setError("");
    try {
      await api.post("/applications", { job_id: id });
      setJob({ ...job, saved: true });
      setMsg("Saved. This only bookmarks the job; it does not mark it as applied.");
    } catch (e) { setError(errMsg(e)); }
  };

  if (error && !job) return <Alert>{error}</Alert>;
  if (!job) return <Spinner />;
  return (
    <>
      <Link to="/jobs">← All jobs</Link>
      <div className="card">
        <h1>{job.title} {job.is_demo && <Badge>Demo</Badge>}</h1>
        <p className="muted">{job.company} · {job.location} · {job.experience}</p>
        {job.is_demo && <DemoNotice />}
        <p>{job.description}</p>
        {job.saved
          ? <p><Badge kind="ok">Saved</Badge> <Link to="/tracker">View in Tracker</Link></p>
          : <button className="btn" onClick={save}>Save job</button>}
        <Alert type="success">{msg}</Alert>
        <Alert>{error}</Alert>
      </div>
      <div className="card">
        <h2>Skill match</h2>
        {job.match ? (
          <>
            <MatchBar percent={job.match.percent} />
            <h3>You have</h3>
            {job.match.matching.length ? <Skills list={job.match.matching} kind="have" /> : <p className="muted">None of the required skills yet.</p>}
            <h3>Missing</h3>
            {job.match.missing.length ? <Skills list={job.match.missing} kind="miss" /> : <p className="muted">Nothing missing. 🎉</p>}
            <p className="muted">Formula: match % = skills you have ÷ skills the job requires × 100. Every skill counts equally. It only compares skill keywords. It is not a prediction of whether you will be hired, and it cannot judge experience or quality.</p>
          </>
        ) : <Empty>Upload your resume to see how you match. <Link to="/resume">Upload</Link></Empty>}
        {!job.match && <Skills list={job.skills} />}
      </div>
      {job.match && <Advice jobId={id} />}
    </>
  );
}
