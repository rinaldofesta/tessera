import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/api";
import { LiveRunPanel } from "@/components/LiveRunPanel";
import { VerdictMosaic } from "@/components/VerdictMosaic";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { ConfirmStep, type RunDraft } from "@/components/launcher/ConfirmStep";
import { CUSTOM, ModelStep } from "@/components/launcher/ModelStep";
import { StepNav, type StepId } from "@/components/launcher/StepNav";
import { SuiteStep } from "@/components/launcher/SuiteStep";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useAsync } from "@/hooks";
import { CONFIRM_COPY, DATASET_LABELS, LIVE_COPY } from "@/copy";
import { messageOf } from "@/lib/format";
import { draftFromRun } from "@/lib/rerun";

/** The starter suite if it exists, else the first available. */
function pickDefaultSuite(suites: { id: string }[]): string {
  return suites.find((s) => s.id === "toy")?.id ?? suites[0]?.id ?? "";
}

export default function Run() {
  const setup = useAsync(() => api.evalSetup(), []);
  const [step, setStep] = useState<StepId>(1);
  const [customId, setCustomId] = useState("");
  const [rescanning, setRescanning] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Snapshot of what was actually submitted — the wizard on the left stays open and
  // editable after launch, so the live panel must not read live `draft`/`questions`,
  // which would drift out from under the run that's actually in flight.
  const [activeRun, setActiveRun] = useState<{
    jobId: string;
    model: string;
    suite: string;
    epochs: number;
    questions: number;
  } | null>(null);
  const [draft, setDraft] = useState<RunDraft>({
    org: "",
    model: "",
    judge: "deterministic",
    grader: null,
    epochs: 3,
  });
  const [params] = useSearchParams();
  const fromId = params.get("from");
  // Which fromId we've already prefilled from, so a fresh /new?from=<id> deep-link
  // still prefills even after an earlier one already completed on this mount.
  const prefilledFor = useRef<string | null>(null);

  // Rerun deep-link: /new?from=<id> copies that run's config and jumps to confirm.
  useEffect(() => {
    if (!fromId || prefilledFor.current === fromId || !setup.data) return;
    let alive = true;
    api
      .listRuns(true)
      .then((runs) => {
        if (!alive) return;
        const source = runs.find((r) => r.id === fromId);
        if (!source) return;
        const known = setup.data!.models.map((m) => m.id);
        const { draft: next, customId: custom } = draftFromRun(source, known);
        setDraft(next);
        if (custom) setCustomId(custom);
        setStep(3);
      })
      .catch(() => {})
      .finally(() => {
        prefilledFor.current = fromId;
      });
    return () => {
      alive = false;
    };
  }, [fromId, setup.data]);

  // Seed server defaults without clobbering user edits.
  useEffect(() => {
    if (!setup.data) return;
    setDraft((current) => ({
      ...current,
      // Prefer the starter suite: suites arrive alphabetically, so taking the first
      // one lands on whichever custom suite sorts earliest — a poor first run.
      org: current.org || pickDefaultSuite(setup.data!.suites),
      epochs: current.epochs || setup.data!.defaults.repeats,
    }));
  }, [setup.data]);

  const models = setup.data?.models ?? [];
  const sources = setup.data?.sources ?? [];
  const questions = useMemo(
    () => setup.data?.suites.find((suite) => suite.id === draft.org)?.questions ?? 0,
    [setup.data, draft.org],
  );
  const effectiveModel = draft.model === CUSTOM ? customId.trim() : draft.model;

  const rescan = async () => {
    setRescanning(true);
    try {
      await api.rescan();
      setup.reload();
    } finally {
      setRescanning(false);
    }
  };

  const launch = async () => {
    // A run from this draft is already showing on the right (the wizard stays on
    // step 3, editable, after launch) — relaunching would silently orphan it.
    // "Run another evaluation" clears activeRun first to allow a deliberate relaunch.
    if (activeRun) return;
    setLaunching(true);
    setError(null);
    try {
      const { job_id } = await api.startRun({
        model: effectiveModel,
        judge: draft.judge,
        org: draft.org,
        epochs: draft.epochs,
        scaffold: "baseline",
        seed: 0,
        ...(draft.judge === "llm" && draft.grader ? { grader: draft.grader } : {}),
      });
      setActiveRun({ jobId: job_id, model: effectiveModel, suite: draft.org, epochs: draft.epochs, questions });
      setLaunching(false);
    } catch (caught) {
      setError(messageOf(caught));
      setLaunching(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl">
      {setup.loading ? (
        <div className="grid gap-3">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <>
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
            <div>
              <StepNav
                current={step}
                chosen={{
                  suite: step > 1 ? (DATASET_LABELS[draft.org] ?? draft.org) : undefined,
                  model: step > 2 ? effectiveModel : undefined,
                }}
                onJump={setStep}
              />
              {step === 1 && (
                <SuiteStep
                  suites={setup.data?.suites ?? []}
                  value={draft.org}
                  onChange={(org) => setDraft((current) => ({ ...current, org }))}
                  onContinue={() => setStep(2)}
                />
              )}
              {step === 2 && (
                <ModelStep
                  models={models}
                  sources={sources}
                  value={draft.model}
                  customId={customId}
                  onChange={(model) => setDraft((current) => ({ ...current, model }))}
                  onCustomId={setCustomId}
                  onRescan={rescan}
                  rescanning={rescanning}
                  onBack={() => setStep(1)}
                  onContinue={() => setStep(3)}
                />
              )}
              {step === 3 && (
                <ConfirmStep
                  draft={{ ...draft, model: effectiveModel }}
                  questions={questions}
                  models={models}
                  onChange={(patch) => setDraft((current) => ({ ...current, ...patch }))}
                  onBack={() => setStep(2)}
                  onLaunch={launch}
                  launching={launching}
                  hasActiveRun={activeRun !== null}
                  error={error}
                />
              )}
            </div>

            <aside>
              {activeRun ? (
                <div className="space-y-3">
                  <LiveRunPanel
                    jobId={activeRun.jobId}
                    questions={activeRun.questions}
                    repeats={activeRun.epochs}
                    model={activeRun.model}
                    suite={activeRun.suite}
                  />
                  <Button variant="ghost" onClick={() => { setActiveRun(null); setLaunching(false); }}>
                    {LIVE_COPY.runAnother}
                  </Button>
                </div>
              ) : (
                <Card className="space-y-4 p-4">
                  <SectionLabel>{LIVE_COPY.willRunTitle}</SectionLabel>
                  <dl className="text-[13px]">
                    {[
                      [CONFIRM_COPY.suite, draft.org],
                      [CONFIRM_COPY.model, effectiveModel],
                      [CONFIRM_COPY.grading, draft.judge === "llm" ? CONFIRM_COPY.llm : CONFIRM_COPY.deterministic],
                      [CONFIRM_COPY.repeats, CONFIRM_COPY.repeatsValue(draft.epochs)],
                    ].map(([key, value], index, rows) => (
                      <div key={key}>
                        <div className="flex justify-between gap-6 py-1.5">
                          <dt className="text-[var(--muted-foreground)]">{key}</dt>
                          <dd className="text-right font-mono">{value}</dd>
                        </div>
                        {index < rows.length - 1 && <Separator />}
                      </div>
                    ))}
                  </dl>
                  <VerdictMosaic questions={questions} repeats={draft.epochs} />
                </Card>
              )}
            </aside>
          </div>
        </>
      )}
    </div>
  );
}
