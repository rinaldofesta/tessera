import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useApiHealth } from "./hooks";
import Dashboard from "./views/Dashboard";
import Datasets from "./views/Datasets";
import Run from "./views/Run";
import Results from "./views/Results";

const NAV = [
  { to: "/dashboard", icon: "📊", label: "Dashboard" },
  { to: "/datasets", icon: "🧩", label: "Datasets" },
  { to: "/run", icon: "▶", label: "Run" },
  { to: "/results", icon: "🔍", label: "Results" },
];

export default function App() {
  const healthy = useApiHealth();
  return (
    <div className="flex h-screen">
      <aside className="w-56 shrink-0 border-r border-border p-3 flex flex-col">
        <div className="flex items-center gap-2 px-2 py-3">
          <span className="text-xl">🧪</span>
          <div>
            <div className="font-bold leading-tight">Tessera</div>
            <div className="text-[11px] text-muted leading-tight">Reliability Explorer</div>
          </div>
        </div>
        <nav className="mt-3 space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm ${
                  isActive ? "bg-panel2 text-ink" : "text-muted hover:bg-panel hover:text-ink"
                }`
              }
            >
              <span className="w-4 text-center">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-3 py-2 text-[11px] text-muted">
          <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${healthy ? "bg-pass" : "bg-fail"}`} />
          API {healthy ? "connected" : "unreachable"}
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-auto">
        <div className="max-w-6xl mx-auto p-6">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/datasets" element={<Datasets />} />
            <Route path="/run" element={<Run />} />
            <Route path="/results" element={<Results />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
