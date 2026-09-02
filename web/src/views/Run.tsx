import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, api } from "@/api";
import { LiveRunPanel } from "@/components/LiveRunPanel";
import { VerdictMosaic } from "@/components/VerdictMosaic";
import { Advanced } from "@/components/run/Advanced";
import { ConnectCard } from "@/components/run/ConnectCard";
import { ModelSelect } from "@/components/run/ModelSelect";
import { SuiteSelect } from "@/components/run/SuiteSelect";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RUN_COPY } from "@/copy";
import { useCatalog } from "@/hooks";
import { messageOf } from "@/lib/format";
import type { Blocker, RunSpec } from "@/types";

function blockersFrom(error: unknown): Blocker[] {
  if (!(error instanceof ApiError) || error.status !== 422 || !Array.isArray(error.detail)) return [];
  return error.detail.filter((value): value is Blocker => (
    typeof value === "object" && value !== null &&
    typeof (value as { code?: unknown }).code === "string" &&
    typeof (value as { message?: unknown }).message === "string"
  ));
}

// Mirrors the two multi-segment/aliased prefixes src/tessera/api/providers.py resolves
// specially (`provider_for_model`) — a naive first-segment split gets both wrong for a
// custom-typed model: MLX's provider id isn't its own first segment, and `grok/` is an
// alias for the `xai` provider, not a distinct "grok" provider.
function providerIdForModel(modelId: string): string {
  if (modelId.startsWith("openai-api/mlx/")) return "mlx";
  if (modelId.startsWith("grok/")) return "xai";
  return modelId.split("/", 1)[0];
}

const REPEAT_OPTIONS = Array.from({ length: 10 }, (_, index) => index + 1);

export default function Run() {
  const { catalog, error: catalogError, reload: reloadCatalog } = useCatalog();
  const [spec, setSpec] = useState<RunSpec | null>(null);
  const [launching, setLaunching] = useState(false);
  const [blockers, setBlockers] = useState<Blocker[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<{
    jobId: string;
    model: string;
    suite: string;
    k: number;
    questions: number;
  } | null>(null);
  const [params] = useSearchParams();
  const fromId = params.get("from");
  const prefilledFor = useRef<string | null>(null);

  useEffect(() => {
    if (!catalog) return;
    setSpec((current) => current ?? {
      model: catalog.models[0]?.id ?? "",
      suite: catalog.defaults.suite,
      engine: catalog.defaults.engine,
      grader: null,
      k: catalog.defaults.k,
      scaffold: catalog.defaults.scaffold,
      seed: catalog.defaults.seed,
    });
  }, [catalog]);

  useEffect(() => {
    if (!fromId || !catalog || !spec || prefilledFor.current === fromId) return;
    // Claim the id before the fetch starts, not after it resolves: `spec` is a
    // dependency (needed to catch the moment defaults first populate it), so every
    // later edit re-runs this effect too — claiming early is what makes the guard
    // above actually stop a second `listRuns` call from firing on each keystroke.
    prefilledFor.current = fromId;
    let alive = true;
    api.listRuns(true)
      .then((runs) => {
        const source = runs.find((run) => run.id === fromId);
        if (!alive || !source) return;
        setSpec((current) => current && ({
          ...current,
          model: source.model,
          suite: source.org,
          engine: source.judge === "llm" ? "llm" : "deterministic",
          grader: source.grader,
          k: source.epochs,
        }));
      })
      .catch(() => {});
    // If the user edits the form before this resolves, the re-run's cleanup flips
    // `alive` false — the prefill is dropped rather than clobbering their edit.
    return () => { alive = false; };
  }, [catalog, fromId, spec]);

  const suite = catalog?.suites.find((candidate) => candidate.name === spec?.suite);
  const model = catalog?.models.find((candidate) => candidate.id === spec?.model);
  const providerId = model?.provider ?? (spec ? providerIdForModel(spec.model) : undefined);
  const provider = catalog?.providers.find((candidate) => candidate.id === providerId);
  const needsConnection = !!provider && (
    !provider.connected || blockers.some((blocker) => blocker.code === "not_connected")
  );
  const advancedBlocked = spec?.engine === "llm" && (
    !spec.grader || spec.grader === spec.model
  );

  const pendingLabel = useMemo(
    () => RUN_COPY.pending(suite?.questions ?? 0, spec?.k ?? 0),
    [spec?.k, suite?.questions],
  );

  async function launch() {
    if (!spec || activeRun || launching || advancedBlocked) return;
    setLaunching(true);
    setBlockers([]);
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
      const nextBlockers = blockersFrom(caught);
      if (nextBlockers.length > 0) setBlockers(nextBlockers);
      else setError(messageOf(caught));
    } finally {
      setLaunching(false);
    }
  }

  function connected() {
    setBlockers((current) => current.filter((blocker) => blocker.code !== "not_connected"));
    reloadCatalog();
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
            onChange={(suite) => setSpec((current) => current && ({ ...current, suite }))} />
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
          {needsConnection && provider ? (
            <ConnectCard provider={provider} onConnected={connected} />
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <Button size="lg" onClick={launch}
                disabled={!spec.model || !spec.suite || advancedBlocked || launching || !!activeRun}>
                {launching ? RUN_COPY.running : RUN_COPY.run}
              </Button>
              <p className="text-xs text-faint">{RUN_COPY.note}</p>
            </div>
          )}
        </div>

        {(error || blockers.length > 0) && (
          <div className="mt-4 grid gap-1 text-sm text-verdict-unreliable" role="alert">
            {error && <p>{error}</p>}
            {blockers.map((blocker) => <p key={`${blocker.code}-${blocker.message}`}>{blocker.message}</p>)}
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
    </div>
  );
}
