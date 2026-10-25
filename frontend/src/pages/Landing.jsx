import { Link } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Landing() {
  const { user } = useAuth();
  return (
    <section className="hero">
      <h1>Know where your resume stands.</h1>
      <p>Upload your resume, see your skills, find jobs that fit, and track every application in one place.</p>
      <Link className="btn big" to={user ? "/resume" : "/register"}>{user ? "Go to my resume" : "Get started free"}</Link>
      <div className="grid three features">
        <div className="card"><h3>1. Analyze</h3><p>Skills are found with a transparent keyword dictionary.</p></div>
        <div className="card"><h3>2. Match</h3><p>See matching and missing skills for each job.</p></div>
        <div className="card"><h3>3. Track</h3><p>Save jobs, then optionally track Applied, Interview and Offer.</p></div>
      </div>
    </section>
  );
}
