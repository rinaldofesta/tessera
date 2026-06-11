import { Suspense, lazy, useEffect } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useApiHealth } from "@/hooks";
import { cn } from "@/lib/utils";

// one chunk per view: recharts (Dashboard's trend line) stays out of the others
const Dashboard = lazy(() => import("@/views/Dashboard"));
const Datasets = lazy(() => import("@/views/Datasets"));
const Results = lazy(() => import("@/views/Results"));
const Run = lazy(() => import("@/views/Run"));

const NAV = [
  { to: "/dashboard", key: "1", label: "dashboard" },
  { to: "/datasets", key: "2", label: "datasets" },
  { to: "/run", key: "3", label: "run" },
  { to: "/results", key: "4", label: "results" },
];

export default function App() {
  const healthy = useApiHealth();
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      // only navigate when nothing interactive owns the keystroke — base-ui
      // popups/dialogs render buttons and role=option divs, not form tags
      if (
        e.metaKey || e.ctrlKey || e.altKey ||
        t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" ||
        t.tagName === "BUTTON" || t.isContentEditable ||
        t.closest?.('[role="dialog"], [role="alertdialog"], [role="listbox"], [role="option"], [role="menu"], [role="combobox"]')
      )
        return;
      const item = NAV.find((n) => n.key === e.key);
      if (item) navigate(item.to);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  return (
    <div className="flex h-screen flex-col">
      <header className="flex h-9 shrink-0 items-center gap-2 border-b border-border px-4 text-xs">
        <span className="font-bold">
          tessera<span className="font-normal text-muted-foreground">@local</span>
        </span>
        <span className="hidden text-muted-foreground sm:inline">· enterprise agent reliability</span>
        <span className="ml-auto tabular-nums">
          {healthy ? (
            <span>[● api:online]</span>
          ) : (
            <span className="bg-foreground px-1 font-bold text-background">[○ api:offline]</span>
          )}
        </span>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-44 shrink-0 flex-col border-r border-border p-2">
          <nav className="space-y-px" aria-label="views">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-1.5 px-2 py-1.5 text-[13px]",
                    isActive
                      ? "bg-foreground font-bold text-background"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="w-3 select-none">{isActive ? "▸" : " "}</span>
                    <span className="flex-1">{n.label}</span>
                    <span className="text-[10px] opacity-50">[{n.key}]</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto space-y-1 px-2 pb-1 text-[10px] leading-relaxed text-muted-foreground">
            <div>[1–4] switch view</div>
            <div>★ pinned example run</div>
            <div className="border-t border-border pt-1">
              pass^k is strict · provenance is read from real tool calls
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1 overflow-auto">
          <div className="mx-auto max-w-6xl p-5">
            <Suspense
              fallback={
                <div className="text-xs text-muted-foreground">
                  <span className="select-none">$ </span>loading view…
                </div>
              }
            >
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/datasets" element={<Datasets />} />
                <Route path="/run" element={<Run />} />
                <Route path="/results" element={<Results />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}
