import { Suspense, lazy } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { NAV_COPY } from "@/copy";
import { useApiHealth } from "@/hooks";
import { cn } from "@/lib/utils";

const Connect = lazy(() => import("@/views/Connect"));
const Datasets = lazy(() => import("@/views/Datasets"));
const Run = lazy(() => import("@/views/Run"));
const Reports = lazy(() => import("@/views/Reports"));
const Report = lazy(() => import("@/views/Report"));

const NAV = [
  { to: "/", label: NAV_COPY.run, end: true },
  { to: "/reports", label: NAV_COPY.reports, end: false },
  { to: "/connect", label: NAV_COPY.connect, end: false },
  { to: "/suites", label: NAV_COPY.suites, end: false },
] as const;

function RootRedirect() {
  const { search } = useLocation();
  return <Navigate to={{ pathname: "/", search }} replace />;
}

function ReportRedirect() {
  const { id = "" } = useParams();
  return <Navigate to={`/reports/${id}`} replace />;
}

export default function App() {
  const healthy = useApiHealth();

  return (
    <div className="min-h-screen bg-background">
      <header className="app-nav border-b border-line bg-panel">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-7 gap-y-3 px-5 py-4 md:px-8">
          <NavLink to="/" className="font-display text-xl font-bold tracking-tight text-foreground">
            {NAV_COPY.brand}
          </NavLink>
          <nav className="order-3 flex w-full flex-wrap items-center gap-1 md:order-none md:w-auto" aria-label={NAV_COPY.label}>
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-raised hover:text-foreground",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground",
                )}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-4">
            <a href="/learn" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              {NAV_COPY.howItWorks}
            </a>
            <span
              role="status"
              aria-label={healthy ? NAV_COPY.apiConnected : NAV_COPY.apiDisconnected}
              title={healthy ? NAV_COPY.apiConnected : NAV_COPY.apiDisconnected}
              className={cn(
                "size-2.5 rounded-full",
                healthy ? "bg-verdict-reliable" : "bg-verdict-unreliable",
              )}
            />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl p-5 md:p-8">
        <Suspense fallback={<div className="rounded-xl border border-line bg-panel p-5 text-sm text-faint">Loading…</div>}>
          <Routes>
            <Route path="/" element={<Run />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/reports/:id" element={<Report />} />
            <Route path="/connect" element={<Connect />} />
            <Route path="/suites" element={<Datasets />} />
            <Route path="/new" element={<RootRedirect />} />
            <Route path="/runs" element={<Navigate to="/reports" replace />} />
            <Route path="/runs/:id" element={<ReportRedirect />} />
            <Route path="/providers" element={<Navigate to="/connect" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
      <Toaster position="bottom-right" richColors closeButton />
    </div>
  );
}
