import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/api";
import { ErrLine, Metric, Panel, SectionLabel, ViewHeader } from "@/components/term";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks";
import { shortModel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ComparisonIntervention, ExperimentComparison, PreflightResult } from "@/types";

function PreflightBadge({ result }: { result: PreflightResult | undefined }) {
  if (!result) return <span className="text-[10px] text-muted-foreground">not checked</span>;
  return (
    <span className={cn(
      "border px-1.5 py-0.5 text-[10px]",
      result.ok ? "border-[var(--verdict-reliable)]/55" : "border-[var(--verdict-unreliable)]/55",
    )}>
      {result.ok ? `ready · ${result.effective_model ?? "identity unreported"}` : result.error}
    </span>
  );
}

export default function Experiments() {
  const [query] = useSearchParams();
  const setup = useAsync(() => api.evalSetup(), []);
  const experiments = useAsync(() => api.listExperiments(), []);
  const [name, setName] = useState("model contrast");
  const [intervention, setIntervention] = useState<
    Extract<ComparisonIntervention, "model" | "scaffold">
  >("model");
  const [baseline, setBaseline] = useState(query.get("baseline") ?? "");
  const [challenger, setChallenger] = useState(query.get("challenger") ?? "");
  const [org, setOrg] = useState(query.get("org") ?? "toy");
  const [repeats, setRepeats] = useState(1);
  const [maxCost, setMaxCost] = useState("");
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState("");
  const [preflights, setPreflights] = useState<Record<string, PreflightResult>>({});
  const [checking, setChecking] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ExperimentComparison | null>(null);

  const models = setup.data?.models ?? [];
  const modelItems = useMemo(() => models.map((model) => ({
    value: model.id,
    label: `${model.label}${model.readiness === "ready" ? "" : ` · ${model.readiness.replace(/_/g, " ")}`}`,
  })), [models]);
  const suiteItems = (setup.data?.suites ?? []).map((suite) => ({ value: suite.id, label: suite.id }));

  useEffect(() => {
    if (modelItems.length < 2) return;
    setBaseline((value) => value || modelItems[0].value);
    setChallenger((value) => value || modelItems.find((item) => item.value !== modelItems[0].value)?.value || "");
  }, [modelItems]);

  useEffect(() => {
    if (!(experiments.data ?? []).some((item) => item.status === "running")) return;
    const timer = window.setInterval(experiments.reload, 2500);
    return () => window.clearInterval(timer);
  }, [experiments.data, experiments.reload]);

  const active = (experiments.data ?? []).find((item) => item.id === selected)
    ?? experiments.data?.[0];
  const baselineVariant = active?.baseline_variant;
  const challengerVariant = active?.request.variants.find((variant) => variant.id !== baselineVariant)?.id;

  async function check(model: string) {
    if (!model) return;
    setChecking(model);
    setError(null);
    try {
      const result = await api.preflight(model);
      setPreflights((current) => ({ ...current, [model]: result }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setChecking(null);
    }
  }

  async function launch() {
    setLaunching(true);
    setError(null);
    setComparison(null);
    try {
      const result = await api.startExperiment({
        name,
        baseline_variant: "baseline",
        intervention,
        repeats,
        max_cost: maxCost ? Number(maxCost) : null,
        max_consecutive_errors: 3,
        variants: [
          {
            id: "baseline", label: "Baseline", model: baseline,
            judge: "deterministic", grader: null, org, epochs: 3,
            scaffold: "baseline", seed: 0,
          },
          {
            id: "challenger", label: "Challenger",
            model: intervention === "model" ? challenger : baseline,
            judge: "deterministic", grader: null, org, epochs: 3,
            scaffold: intervention === "scaffold" ? "refuse-aware" : "baseline", seed: 0,
          },
        ],
      });
      setSelected(result.experiment_id);
      experiments.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLaunching(false);
    }
  }

  async function compareActive() {
    if (!active || !challengerVariant) return;
    setError(null);
    try {
      setComparison(await api.compareExperiment(
        active.id, challengerVariant, active.request.intervention ?? "model",
      ));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function resumeActive() {
    if (!active) return;
    setError(null);
    try {
      await api.resumeExperiment(active.id);
      experiments.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  return (
    <div className="space-y-4">
      <ViewHeader
        cmd="tessera experiment"
        desc="change one dimension, run a resumable matrix, and compare paired evidence against a declared baseline"
      />
      {error && <ErrLine msg={error} />}
      {setup.error && <ErrLine msg={setup.error} />}
      {experiments.error && <ErrLine msg={experiments.error} />}

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel title="new controlled experiment" className="xl:col-span-2">
          {setup.loading ? <Skeleton className="h-48 w-full" /> : (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <SectionLabel>experiment name</SectionLabel>
                  <Input value={name} onChange={(event) => setName(event.target.value)} />
                </div>
                <div>
                  <SectionLabel>test suite</SectionLabel>
                  <Select value={org} onValueChange={(value) => setOrg(value as string)} items={suiteItems}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>{suiteItems.map((item) => (
                      <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                    ))}</SelectContent>
                  </Select>
                </div>
                <div>
                  <SectionLabel>one intended change</SectionLabel>
                  <Select
                    value={intervention}
                    onValueChange={(value) => setIntervention(value as typeof intervention)}
                    items={[
                      { value: "model", label: "model" },
                      { value: "scaffold", label: "refusal scaffold" },
                    ]}
                  >
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="model">model</SelectItem>
                      <SelectItem value="scaffold">refusal scaffold</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className={cn("grid gap-3", intervention === "model" && "md:grid-cols-2")}>
                {([
                  {
                    label: intervention === "model" ? "baseline model" : "model under test",
                    value: baseline, set: setBaseline,
                  },
                  ...(intervention === "model"
                    ? [{ label: "challenger model", value: challenger, set: setChallenger }]
                    : []),
                ] as const).map((arm) => (
                  <div key={arm.label} className="border border-border p-3">
                    <SectionLabel>{arm.label}</SectionLabel>
                    <Select value={arm.value} onValueChange={(value) => arm.set(value as string)} items={modelItems}>
                      <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>{modelItems.map((item) => (
                        <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                      ))}</SelectContent>
                    </Select>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <PreflightBadge result={preflights[arm.value]} />
                      <Button
                        size="xs" variant="ghost" disabled={!arm.value || checking === arm.value}
                        onClick={() => check(arm.value)}
                      >
                        {checking === arm.value ? "checking…" : "paid capability check"}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <SectionLabel>independent run repeats</SectionLabel>
                  <Input type="number" min={1} max={10} value={repeats} onChange={(event) => setRepeats(Number(event.target.value))} />
                </div>
                <div>
                  <SectionLabel>cost ceiling (optional USD)</SectionLabel>
                  <Input type="number" min="0.01" step="0.01" value={maxCost} placeholder="no ceiling" onChange={(event) => setMaxCost(event.target.value)} />
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
                <p className="text-[10px] text-muted-foreground">
                  capability checks are optional and make a small paid call; listing a model alone does not prove tool support
                </p>
                <Button
                  onClick={launch}
                  disabled={launching || !name || !baseline || (
                    intervention === "model" && (!challenger || baseline === challenger)
                  )}
                >
                  {launching ? "starting…" : `run ${repeats * 2} cells`}
                </Button>
              </div>
            </div>
          )}
        </Panel>

        <Panel title={`experiments (${experiments.data?.length ?? 0})`} bodyClassName="p-0">
          {experiments.loading && <div className="p-3"><Skeleton className="h-24 w-full" /></div>}
          {(experiments.data ?? []).map((experiment) => {
            const done = experiment.cells.filter((cell) => cell.status === "done").length;
            return (
              <button
                key={experiment.id} onClick={() => { setSelected(experiment.id); setComparison(null); }}
                className={cn(
                  "block w-full border-b border-border px-3 py-2 text-left text-xs last:border-0",
                  active?.id === experiment.id ? "bg-foreground text-background" : "hover:bg-muted",
                )}
              >
                <div className="flex justify-between gap-2 font-bold">
                  <span className="truncate">{experiment.name}</span><span>{experiment.status}</span>
                </div>
                <div className={cn("mt-1 flex justify-between text-[10px]", active?.id === experiment.id ? "text-background/70" : "text-muted-foreground")}>
                  <span>{done}/{experiment.cells.length} cells</span>
                  <span>{experiment.total_cost == null ? "cost unknown" : `$${experiment.total_cost.toFixed(4)}`}</span>
                </div>
              </button>
            );
          })}
          {!experiments.loading && experiments.data?.length === 0 && (
            <div className="p-3 text-xs text-muted-foreground">no experiments yet</div>
          )}
        </Panel>
      </div>

      {active && (
        <Panel
          title={`matrix — ${active.name}`}
          right={<div className="flex gap-2">
            {(active.status === "error" || active.status === "stopped") && (
              <Button size="xs" variant="ghost" onClick={resumeActive}>resume missing cells</Button>
            )}
            {active.status === "done" && challengerVariant && (
              <Button size="xs" variant="outline" onClick={compareActive}>compare with baseline</Button>
            )}
          </div>}
          bodyClassName="space-y-3"
        >
          <div className="grid gap-2 sm:grid-cols-4">
            <Metric label="status" value={active.status} />
            <Metric label="cells" value={`${active.cells.filter((cell) => cell.status === "done").length}/${active.cells.length}`} />
            <Metric label="cost" value={active.total_cost == null ? "unknown" : `$${active.total_cost.toFixed(4)}`} />
            <Metric label="baseline" value={baselineVariant ?? "—"} />
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {active.request.variants.map((variant) => (
              <div key={variant.id} className="border border-border p-3">
                <div className="mb-2 flex justify-between text-xs font-bold">
                  <span>{variant.label} · {shortModel(variant.model)}</span>
                  {variant.id === baselineVariant && <span className="text-[10px] uppercase text-muted-foreground">baseline</span>}
                </div>
                <div className="flex flex-wrap gap-2">
                  {active.cells.filter((cell) => cell.variant_id === variant.id).map((cell) => (
                    cell.run_id ? (
                      <Link key={cell.id} to={`/runs/${cell.run_id}`} className="border border-border px-2 py-1 text-[10px] hover:bg-muted">
                        #{cell.repeat_index} · {cell.status}
                      </Link>
                    ) : (
                      <span key={cell.id} className="border border-border px-2 py-1 text-[10px] text-muted-foreground">
                        #{cell.repeat_index} · {cell.status}
                      </span>
                    )
                  ))}
                </div>
              </div>
            ))}
          </div>
          {active.error && <ErrLine msg={active.error} />}
        </Panel>
      )}

      {comparison && (
        <Panel title="paired experiment result">
          <div className="grid gap-2 sm:grid-cols-4">
            <Metric label="paired observations" value={String(comparison.overall.matched)} />
            <Metric label="baseline only passes" value={String(comparison.overall.a_wins)} />
            <Metric label="challenger only passes" value={String(comparison.overall.b_wins)} />
            <Metric label="exact p" value={comparison.overall.p_value < 0.0001 ? "<0.0001" : comparison.overall.p_value.toFixed(4)} />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            paired independent repeats: {comparison.paired_repeats.join(", ")}; changed dimensions: {comparison.changed_dimensions.join(", ")}
          </p>
        </Panel>
      )}
    </div>
  );
}
