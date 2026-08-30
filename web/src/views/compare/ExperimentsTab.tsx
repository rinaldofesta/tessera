import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/api";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { StatTile } from "@/components/viz/StatTile";
import { EXPERIMENTS_COPY as C } from "@/copy";
import { useAsync } from "@/hooks";
import { shortModel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  ComparisonIntervention,
  ExperimentComparison,
  PreflightResult,
} from "@/types";

function PreflightBadge({ result }: { result: PreflightResult | undefined }) {
  if (!result)
    return <Badge variant="outline" className="text-[10px] text-muted-foreground">{C.preflightUnchecked}</Badge>;
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-[10px]",
        result.ok
          ? "text-verdict-reliable"
          : "text-verdict-unreliable",
      )}
    >
      {result.ok ? C.preflightReady(result.effective_model) : result.error}
    </Badge>
  );
}

export default function ExperimentsTab() {
  const [query] = useSearchParams();
  const setup = useAsync(() => api.evalSetup(), []);
  const experiments = useAsync(() => api.listExperiments(), []);
  const [name, setName] = useState<string>(C.defaultName);
  const [intervention, setIntervention] =
    useState<Extract<ComparisonIntervention, "model" | "scaffold">>("model");
  const [baseline, setBaseline] = useState(query.get("baseline") ?? "");
  const [challenger, setChallenger] = useState(query.get("challenger") ?? "");
  const [org, setOrg] = useState(query.get("org") ?? "toy");
  const [repeats, setRepeats] = useState(1);
  const [maxCost, setMaxCost] = useState("");
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState("");
  const [preflights, setPreflights] = useState<Record<string, PreflightResult>>(
    {},
  );
  const [checking, setChecking] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ExperimentComparison | null>(
    null,
  );
  const models = setup.data?.models ?? [];
  const modelItems = useMemo(
    () =>
      models.map((model) => ({
        value: model.id,
        label: `${model.label}${model.readiness === "ready" ? "" : ` · ${model.readiness.replace(/_/g, " ")}`}`,
      })),
    [models],
  );
  const suiteItems = (setup.data?.suites ?? []).map((suite) => ({
    value: suite.id,
    label: suite.id,
  }));
  useEffect(() => {
    if (modelItems.length < 2) return;
    setBaseline((value) => value || modelItems[0].value);
    setChallenger(
      (value) =>
        value ||
        modelItems.find((item) => item.value !== modelItems[0].value)?.value ||
        "",
    );
  }, [modelItems]);
  useEffect(() => {
    if (!(experiments.data ?? []).some((item) => item.status === "running"))
      return;
    const timer = window.setInterval(experiments.reload, 2500);
    return () => window.clearInterval(timer);
  }, [experiments.data, experiments.reload]);
  const active =
    (experiments.data ?? []).find((item) => item.id === selected) ??
    experiments.data?.[0];
  const baselineVariant = active?.baseline_variant;
  const challengerVariant = active?.request.variants.find(
    (variant) => variant.id !== baselineVariant,
  )?.id;
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
            id: "baseline",
            label: "Baseline",
            model: baseline,
            judge: "deterministic",
            grader: null,
            org,
            epochs: 3,
            scaffold: "baseline",
            seed: 0,
          },
          {
            id: "challenger",
            label: "Challenger",
            model: intervention === "model" ? challenger : baseline,
            judge: "deterministic",
            grader: null,
            org,
            epochs: 3,
            scaffold: intervention === "scaffold" ? "refuse-aware" : "baseline",
            seed: 0,
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
      setComparison(
        await api.compareExperiment(
          active.id,
          challengerVariant,
          active.request.intervention ?? "model",
        ),
      );
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
    <div className="space-y-4 pt-4">
      {[
        ["local", error],
        ["setup", setup.error],
        ["experiments", experiments.error],
      ].filter(([, detail]) => Boolean(detail)).map(([source, detail]) => (
        <Alert key={source} variant="destructive">
          <AlertDescription>{C.error(detail!)}</AlertDescription>
        </Alert>
      ))}
      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="p-4 xl:col-span-2">
          <SectionLabel>{C.createTitle}</SectionLabel>
          {setup.loading ? (
            <Skeleton className="h-48 w-full" />
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <SectionLabel>{C.experimentName}</SectionLabel>
                  <Input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                </div>
                <div>
                  <SectionLabel>{C.testSuite}</SectionLabel>
                  <Select
                    value={org}
                    onValueChange={(value) => setOrg(value as string)}
                    items={suiteItems}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {suiteItems.map((item) => (
                        <SelectItem key={item.value} value={item.value}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <SectionLabel>{C.intendedChange}</SectionLabel>
                  <Select
                    value={intervention}
                    onValueChange={(value) =>
                      setIntervention(value as typeof intervention)
                    }
                    items={[
                      { value: "model", label: C.model },
                      { value: "scaffold", label: C.refusalScaffold },
                    ]}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="model">{C.model}</SelectItem>
                      <SelectItem value="scaffold">
                        {C.refusalScaffold}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div
                className={cn(
                  "grid gap-3",
                  intervention === "model" && "md:grid-cols-2",
                )}
              >
                {(
                  [
                    {
                      label:
                        intervention === "model"
                          ? C.baselineModel
                          : C.modelUnderTest,
                      value: baseline,
                      set: setBaseline,
                    },
                    ...(intervention === "model"
                      ? [
                          {
                            label: C.challengerModel,
                            value: challenger,
                            set: setChallenger,
                          },
                        ]
                      : []),
                  ] as const
                ).map((arm) => (
                  <Card key={arm.label} className="rounded-md p-3">
                    <SectionLabel>{arm.label}</SectionLabel>
                    <Select
                      value={arm.value}
                      onValueChange={(value) => arm.set(value as string)}
                      items={modelItems}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {modelItems.map((item) => (
                          <SelectItem key={item.value} value={item.value}>
                            {item.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <PreflightBadge result={preflights[arm.value]} />
                      <Button
                        size="xs"
                        variant="ghost"
                        disabled={!arm.value || checking === arm.value}
                        onClick={() => check(arm.value)}
                      >
                        {checking === arm.value ? C.checking : C.paidCheck}
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <SectionLabel>{C.repeats}</SectionLabel>
                  <Input
                    type="number"
                    min={1}
                    max={10}
                    value={repeats}
                    onChange={(event) => setRepeats(Number(event.target.value))}
                  />
                </div>
                <div>
                  <SectionLabel>{C.costCeiling}</SectionLabel>
                  <Input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={maxCost}
                    placeholder={C.noCeiling}
                    onChange={(event) => setMaxCost(event.target.value)}
                  />
                </div>
              </div>
              <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
                <p className="text-[10px] text-muted-foreground">
                  {C.checkHint}
                </p>
                <Button
                  onClick={launch}
                  disabled={
                    launching ||
                    !name ||
                    !baseline ||
                    (intervention === "model" &&
                      (!challenger || baseline === challenger))
                  }
                >
                  {launching ? C.starting : C.runCells(repeats * 2)}
                </Button>
              </div>
            </div>
          )}
        </Card>
        <Card className="p-0">
          <div className="p-4 pb-2">
            <SectionLabel>
              {C.experiments(experiments.data?.length ?? 0)}
            </SectionLabel>
          </div>
          {experiments.loading && (
            <div className="p-3">
              <Skeleton className="h-24 w-full" />
            </div>
          )}
          {(experiments.data ?? []).map((experiment) => {
            const done = experiment.cells.filter(
              (cell) => cell.status === "done",
            ).length;
            return (
              <button
                key={experiment.id}
                onClick={() => {
                  setSelected(experiment.id);
                  setComparison(null);
                }}
                className={cn(
                  "block w-full border-b border-border px-3 py-2 text-left text-xs last:border-0",
                  active?.id === experiment.id
                    ? "bg-primary/10"
                    : "hover:bg-muted",
                )}
              >
                <div className="flex justify-between gap-2 font-bold">
                  <span className="truncate">{experiment.name}</span>
                  <span>{experiment.status}</span>
                </div>
                <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                  <span>{C.cells(done, experiment.cells.length)}</span>
                  <span>
                    {experiment.total_cost == null
                      ? C.costUnknown
                      : `$${experiment.total_cost.toFixed(4)}`}
                  </span>
                </div>
              </button>
            );
          })}
          {!experiments.loading && experiments.data?.length === 0 && (
            <div className="p-3 text-xs text-muted-foreground">
              {C.noExperiments}
            </div>
          )}
        </Card>
      </div>
      {active && (
        <Card className="space-y-3 p-4">
          <div className="flex items-center justify-between gap-3">
            <SectionLabel>{C.matrix(active.name)}</SectionLabel>
            <div className="flex gap-2">
              {(active.status === "error" || active.status === "stopped") && (
                <Button size="xs" variant="ghost" onClick={resumeActive}>
                  {C.resume}
                </Button>
              )}
              {active.status === "done" && challengerVariant && (
                <Button size="xs" variant="outline" onClick={compareActive}>
                  {C.compare}
                </Button>
              )}
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-4">
            <StatTile label={C.status} value={active.status} />
            <StatTile
              label={C.cellCount}
              value={`${active.cells.filter((cell) => cell.status === "done").length}/${active.cells.length}`}
            />
            <StatTile
              label={C.cost}
              value={
                active.total_cost == null
                  ? C.unknown
                  : `$${active.total_cost.toFixed(4)}`
              }
            />
            <StatTile label={C.baseline} value={baselineVariant ?? C.noBaseline} />
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {active.request.variants.map((variant) => (
              <Card key={variant.id} className="rounded-md p-3">
                <div className="mb-2 flex justify-between text-xs font-bold">
                  <span>
                    {variant.label} · {shortModel(variant.model)}
                  </span>
                  {variant.id === baselineVariant && (
                    <span className="text-[10px] uppercase text-muted-foreground">
                      {C.baseline}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {active.cells
                    .filter((cell) => cell.variant_id === variant.id)
                    .map((cell) =>
                      cell.run_id ? (
                        <Link
                          key={cell.id}
                          to={`/runs/${cell.run_id}`}
                          className="border border-border px-2 py-1 text-[10px] hover:bg-muted"
                        >
                          #{cell.repeat_index} · {cell.status}
                        </Link>
                      ) : (
                        <span
                          key={cell.id}
                          className="border border-border px-2 py-1 text-[10px] text-muted-foreground"
                        >
                          #{cell.repeat_index} · {cell.status}
                        </span>
                      ),
                    )}
                </div>
              </Card>
            ))}
          </div>
          {active.error && (
            <Alert variant="destructive">
              <AlertDescription>{active.error}</AlertDescription>
            </Alert>
          )}
        </Card>
      )}
      {comparison && (
        <Card className="p-4">
          <SectionLabel>{C.pairedResult}</SectionLabel>
          <div className="grid gap-2 sm:grid-cols-4">
            <StatTile
              label={C.pairedObservations}
              value={String(comparison.overall.matched)}
            />
            <StatTile
              label={C.baselineOnly}
              value={String(comparison.overall.a_wins)}
            />
            <StatTile
              label={C.challengerOnly}
              value={String(comparison.overall.b_wins)}
            />
            <StatTile
              label={C.exactP}
              value={
                comparison.overall.p_value < 0.0001
                  ? "<0.0001"
                  : comparison.overall.p_value.toFixed(4)
              }
            />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            {C.pairedRepeats(
              comparison.paired_repeats,
              comparison.changed_dimensions,
            )}
          </p>
        </Card>
      )}
    </div>
  );
}
