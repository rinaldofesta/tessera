import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api";
import { ConfirmStep, type RunDraft } from "@/components/launcher/ConfirmStep";
import { CUSTOM, ModelStep } from "@/components/launcher/ModelStep";
import { StepNav, type StepId } from "@/components/launcher/StepNav";
import { SuiteStep } from "@/components/launcher/SuiteStep";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks";
import { DATASET_LABELS } from "@/copy";

/** The starter suite if it exists, else the first available. */
function pickDefaultSuite(suites: { id: string }[]): string {
  return suites.find((s) => s.id === "toy")?.id ?? suites[0]?.id ?? "";
}

export default function Run() {
  const navigate = useNavigate();
  const setup = useAsync(() => api.evalSetup(), []);
  const [step, setStep] = useState<StepId>(1);
  const [customId, setCustomId] = useState("");
  const [rescanning, setRescanning] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<RunDraft>({
    org: "",
    model: "",
    judge: "deterministic",
    grader: null,
    epochs: 3,
  });

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
    setLaunching(true);
    setError(null);
    try {
      const { job_id } = await api.startRun({
        model: effectiveModel,
        judge: draft.judge,
        org: draft.org,
        epochs: draft.epochs,
        ...(draft.judge === "llm" && draft.grader ? { grader: draft.grader } : {}),
      });
      navigate(`/runs/${job_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      setLaunching(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl">
      {setup.loading ? (
        <div className="grid gap-3">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <>
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
              error={error}
            />
          )}
        </>
      )}
    </div>
  );
}
