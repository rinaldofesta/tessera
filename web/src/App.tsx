import { Suspense, lazy, useEffect } from "react";
import {
  CircleHelp,
  ExternalLink,
  Home,
  Library,
  KeyRound,
  ListChecks,
  Plus,
  Trophy,
} from "lucide-react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { SHELL_COPY } from "@/copy";
import { useApiHealth } from "@/hooks";
import { DEV_API_HOST } from "@/lib/backend";
import { cn } from "@/lib/utils";

// one chunk per view: recharts (Dashboard's trend line) stays out of the others
const Dashboard = lazy(() => import("@/views/Dashboard"));
const Datasets = lazy(() => import("@/views/Datasets"));
const Leaderboard = lazy(() => import("@/views/Leaderboard"));
const Providers = lazy(() => import("@/views/Providers"));
const RunMonitor = lazy(() => import("@/views/RunMonitor"));
const Results = lazy(() => import("@/views/Results"));
const Run = lazy(() => import("@/views/Run"));

const NAV = [
  { to: "/", key: "1", label: SHELL_COPY.navItems.home, icon: Home, end: true },
  { to: "/runs", key: "2", label: SHELL_COPY.navItems.runs, icon: ListChecks, end: false },
  { to: "/suites", key: "3", label: SHELL_COPY.navItems.suites, icon: Library, end: false },
  {
    to: "/providers",
    key: "4",
    label: SHELL_COPY.navItems.providers,
    icon: KeyRound,
    end: false,
  },
  {
    to: "/leaderboard",
    key: "5",
    label: SHELL_COPY.navItems.leaderboard,
    icon: Trophy,
    end: false,
  },
] as const;

export default function App() {
  const healthy = useApiHealth();
  const navigate = useNavigate();
  // in dev the SPA runs on vite's port and proxies /api to the backend; in the
  // shipped app FastAPI serves this page itself, so the origin is already the backend's
  const apiOrigin = import.meta.env.DEV ? DEV_API_HOST : window.location.host;

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
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-card px-4 py-5">
        <div className="px-2 font-display text-2xl font-bold tracking-[-0.04em] text-foreground">
          {SHELL_COPY.brand}
        </div>

        <Button
          size="lg"
          className="mt-6 w-full justify-start gap-2 shadow-sm shadow-primary/10"
          // it renders an anchor, not a <button> — base-ui needs telling, or it
          // strips the link's native semantics
          nativeButton={false}
          render={<NavLink to="/new" />}
        >
          <Plus aria-hidden="true" />
          {SHELL_COPY.newEvaluation}
        </Button>

        <nav className="mt-7 space-y-1" aria-label={SHELL_COPY.navLabel}>
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "relative flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:rounded-full before:bg-primary before:opacity-0",
                    isActive
                      ? "bg-primary/10 font-semibold text-primary before:opacity-100"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  )
                }
              >
                <Icon aria-hidden="true" className="size-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-border px-2 pt-5">
          <div
            className={cn(
              "flex items-start gap-2 text-xs",
              healthy ? "text-muted-foreground" : "font-medium text-verdict-unreliable",
            )}
            aria-live="polite"
          >
            <span
              aria-hidden="true"
              className={cn(
                "mt-1 size-2 shrink-0 rounded-full",
                healthy ? "bg-verdict-reliable" : "bg-verdict-unreliable",
              )}
            />
            <span>
              {healthy ? SHELL_COPY.apiConnected : SHELL_COPY.apiDisconnected}
              <span aria-hidden="true"> · </span>
              <span
                title={SHELL_COPY.apiOriginHint}
                className={cn("font-mono text-[11px]", healthy && "text-faint")}
              >
                {apiOrigin}
              </span>
            </span>
          </div>

          <p className="mt-4 text-[11px] text-faint">{SHELL_COPY.shortcuts}</p>

          <a
            href="/learn"
            target="_blank"
            rel="noreferrer"
            className="mt-4 flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <CircleHelp aria-hidden="true" className="size-4" />
            <span>{SHELL_COPY.help}</span>
            <ExternalLink aria-hidden="true" className="ml-auto size-3.5" />
          </a>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-7xl p-8">
          <Suspense
            fallback={
              <div className="rounded-lg border border-border bg-card p-5 text-sm text-muted-foreground">
                Loading view…
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/runs" element={<Results />} />
              <Route path="/runs/:id" element={<RunMonitor />} />
              <Route path="/suites" element={<Datasets />} />
              <Route path="/leaderboard" element={<Leaderboard />} />
              <Route path="/new" element={<Run />} />
              <Route path="/providers" element={<Providers />} />

              <Route path="/dashboard" element={<Navigate to="/" replace />} />
              <Route path="/datasets" element={<Navigate to="/suites" replace />} />
              <Route path="/run" element={<Navigate to="/new" replace />} />
              <Route path="/results" element={<Navigate to="/runs" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </div>
      </main>
      <Toaster position="bottom-right" richColors closeButton />
    </div>
  );
}
