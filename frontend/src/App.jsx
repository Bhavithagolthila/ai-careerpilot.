import { Route, Routes } from "react-router-dom";
import { Navbar, ProtectedRoute } from "./components";
import Landing from "./pages/Landing";
import { Login, Register } from "./pages/AuthPages";
import Resume from "./pages/Resume";
import { Jobs, JobDetail } from "./pages/Jobs";
import Tracker from "./pages/Tracker";

const P = ({ children }) => <ProtectedRoute>{children}</ProtectedRoute>;

export default function App() {
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/resume" element={<P><Resume /></P>} />
          <Route path="/jobs" element={<P><Jobs /></P>} />
          <Route path="/jobs/:id" element={<P><JobDetail /></P>} />
          <Route path="/tracker" element={<P><Tracker /></P>} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </>
  );
}
