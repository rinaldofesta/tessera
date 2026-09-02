import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/api";
import { LiveRunPanel } from "@/components/LiveRunPanel";
import { VerdictMosaic } from "@/components/VerdictMosaic";
import { Advanced } from "@/components/run/Advanced";
import { ConnectCard } from "@/components/run/ConnectCard";
import { ModelSelect } from "@/components/run/ModelSelect";
import { SuiteSelect } from "@/components/run/SuiteSelect";
import { SuiteSheet, withSuiteEdit } from "@/components/suite/SuiteSheet";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RUN_COPY, SUITE_COPY } from "@/copy";
import { useCatalog } from "@/hooks";
import { messageOf } from "@/lib/format";
import type { Plan, RunSpec } from "@/types";

const REPEAT_OPTIONS = Array.from({ length: 10 }, (_, index) => index + 1);

export default function Run() {
  const { catalog, error: catalogError, reload: reloadCatalog } = useCatalog();
  const [spec, setSpec] = useState<RunSpec | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [planNonce, setPlanNonce] = useState(0);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<{
    jobId: string;
    model: string;
    suite: string;
    k: number;
    questions: number;
  } | null>(null);
  const [params, setParams] = useSearchParams();

  useEffect(() => {
    if (!catalog) return;
    setSpec((current) => {
      if (current) return current;
      const numeric = (key: "k" | "seed", fallback: number) => {
        const raw = params.get(key);
        // `raw` guards the empty string too — Number("") is 0, which is finite, so
        // `k=&seed=` in the URL would otherwise silently launch with zero repeats.
        const value = raw ? Number(raw) : NaN;
        return Number.isFinite(value) ? value : fallback;
      };
      const engine = params.get("engine");
      return {
        model: params.get("model") ?? catalog.models[0]?.id ?? "",
        suite: catalog.suites.some((suite) => suite.name === params.get("suite"))
          ? params.get("suite") as string
          : catalog.defaults.suite,
        engine: engine === "llm" || engine === "deterministic" ? engine : catalog.defaults.engine,
        grader: params.has("grader") ? params.get("grader") || null : null,
        k: numeric("k", catalog.defaults.k),
        scaffold: params.get("scaffold") ?? catalog.defaults.scaffold,
        seed: numeric("seed", catalog.defaults.seed),
      };
    });
  }, [catalog, params]);

  useEffect(() => {
    if (!spec) return;
    let active = true;
    setPlan(null);
    setError(null);
    const timer = setTimeout(() => {
      api.dryRun(spec)
        .then((next) => { if (active) setPlan(next); })
        .catch((caught) => { if (active) setError(messageOf(caught)); });
    }, 300);
    return () => { active = false; clearTimeout(timer); };
  }, [spec, planNonce]);

  const suite = catalog?.suites.find((candidate) => candidate.name === spec?.suite);
  const provider = catalog?.providers.find((candidate) => candidate.id === plan?.provider);
  const connectionBlocker = plan?.blockers.find((blocker) => blocker.code === "not_connected");

  const pendingLabel = useMemo(
    () => RUN_COPY.pending(suite?.questions ?? 0, spec?.k ?? 0),
    [spec?.k, suite?.questions],
  );

  async function launch() {
    if (!spec || !plan?.ready || activeRun || launching) return;
    setLaunching(true);
    setError(null);
    try {
      const run = await api.startRun(spec);
      setActiveRun({
        jobId: run.id,
        model: spec.model,
        suite: spec.suite,
        k: spec.k,
        questions: suite?.questions ?? 0,
      });
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      setLaunching(false);
    }
  }

  function connected() {
    reloadCatalog();
    setPlanNonce((nonce) => nonce + 1);
  }

  function manageSuites() {
    setParams((current) => withSuiteEdit(current, "new"));
  }

  if (!catalog || !spec) {
    return catalogError ? (
      <p className="text-sm text-verdict-unreliable">{catalogError}</p>
    ) : (
      <div className="grid gap-3"><Skeleton className="h-12 w-3/4" /><Skeleton className="h-56" /></div>
    );
  }

  return (
    <div className="mx-auto grid max-w-6xl items-start gap-6 md:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <section className="min-w-0 py-4">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-3 font-display text-2xl font-medium leading-relaxed md:text-3xl">
          <span>{RUN_COPY.ask}</span>
          <ModelSelect models={catalog.models} providers={catalog.providers} value={spec.model}
            onChange={(model) => setSpec((current) => current && ({ ...current, model }))} />
          <span>{RUN_COPY.the}</span>
          <SuiteSelect suites={catalog.suites} value={spec.suite}
            onChange={(suite) => setSpec((current) => current && ({ ...current, suite }))}
            onManage={manageSuites} />
          <button className="text-xs font-sans font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" onClick={manageSuites}>
            {SUITE_COPY.manage}
          </button>
          <span>{RUN_COPY.questions}</span>
          <select
            aria-label={RUN_COPY.repeatsLabel}
            className="h-10 rounded-lg border border-line bg-raised px-3 font-medium text-primary outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
            value={spec.k}
            onChange={(event) => setSpec((current) => current && ({ ...current, k: Number(event.target.value) }))}
          >
            {REPEAT_OPTIONS.map((k) => <option key={k}>{k}</option>)}
          </select>
          <span>{RUN_COPY.timesEach}</span>
        </div>

        <Advanced spec={spec} models={catalog.models} scaffolds={catalog.scaffolds}
          onChange={(patch) => setSpec((current) => current && ({ ...current, ...patch }))} />

        <div className="mt-6">
          {connectionBlocker && provider ? (
            <ConnectCard provider={provider} onConnected={connected} />
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <Button size="lg" onClick={launch}
                disabled={!plan?.ready || launching || !!activeRun}>
                {launching ? RUN_COPY.running : RUN_COPY.run}
              </Button>
              <p className="text-xs text-faint">{RUN_COPY.note}</p>
            </div>
          )}
        </div>

        {(error || (plan?.blockers.length ?? 0) > 0) && (
          <div className="mt-4 grid gap-1 text-sm text-verdict-unreliable" role="alert">
            {error && <p>{error}</p>}
            {plan?.blockers.map((blocker) => <p key={`${blocker.code}-${blocker.message}`}>{blocker.message}</p>)}
          </div>
        )}
      </section>

      <aside className="min-w-0">
        {activeRun ? (
          <div className="grid gap-3">
            <LiveRunPanel jobId={activeRun.jobId} questions={activeRun.questions}
              repeats={activeRun.k} model={activeRun.model} suite={activeRun.suite} />
            <Button variant="ghost" onClick={() => setActiveRun(null)}>{RUN_COPY.runAnother}</Button>
          </div>
        ) : (
          <Card className="gap-4 border border-line bg-panel p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-faint">{pendingLabel}</p>
            <VerdictMosaic questions={suite?.questions ?? 0} repeats={spec.k} size="lg" />
          </Card>
        )}
      </aside>
      <SuiteSheet
        onSaved={(suiteName) => setSpec((current) => current && ({ ...current, suite: suiteName }))}
        onDeleted={(deletedName) => setSpec((current) => current && current.suite === deletedName
          ? { ...current, suite: catalog.defaults.suite }
          : current)}
      />
    </div>
  );
}
