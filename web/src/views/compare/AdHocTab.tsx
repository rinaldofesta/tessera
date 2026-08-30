import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api";
import { EvaluationDetail } from "@/components/EvaluationDetail";
import { Scorecard } from "@/components/Scorecard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CategoryBars } from "@/components/viz/CategoryBars";
import { GapBar } from "@/components/viz/GapBar";
import { RunPicker } from "@/components/viz/RunPicker";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { COMPARE_COPY, COMPARE_PALETTE, conflictLabel } from "@/copy";
import { useAsync } from "@/hooks";
import { driftSummary, parseEvalsParam, planPairs, type PairOutcome } from "@/lib/comparePlan";
import { downloadComparison } from "@/lib/exportComparison";
import { shortModel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ComparisonIntervention, Diagnostic, Report } from "@/types";

const INTERVENTIONS: { value: ComparisonIntervention; label: string }[] = [
  { value: "model", label: "model" },
  { value: "scaffold", label: "scaffold" },
  { value: "harness", label: "harness" },
  { value: "grader", label: "grader" },
  { value: "engine", label: "scoring engine" },
  { value: "org", label: "test suite" },
  { value: "seed", label: "dataset seed" },
  { value: "k", label: "repeat count" },
];

type Metric = keyof typeof COMPARE_COPY.metricTabs;

const METRICS = Object.keys(COMPARE_COPY.metricTabs) as Metric[];

const messageOf = (error: unknown) => error instanceof Error ? error.message : String(error);

const pValue = (value: number) => value < 0.0001 ? "< 0.0001" : value.toFixed(4);

export default function AdHocTab() {
  const [searchParams] = useSearchParams();
  const evaluations = useAsync(() => api.listEvaluations(), []);
  const [selected, setSelected] = useState<string[]>([]);
  const seeded = useRef(false);
  const [intervention, setIntervention] = useState<ComparisonIntervention>("model");
  const [pairs, setPairs] = useState<PairOutcome[] | null>(null);
  const [pairsLoading, setPairsLoading] = useState(false);
  const [pairsError, setPairsError] = useState<string | null>(null);
  const [reports, setReports] = useState<Record<string, Report>>({});
  const [reportsLoading, setReportsLoading] = useState(false);
  const [reportsError, setReportsError] = useState<string | null>(null);
  const [metric, setMetric] = useState<Metric>("reliability");
  const [inspected, setInspected] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<{
    loading: boolean;
    error: string | null;
    data: Diagnostic[] | null;
  }>({ loading: false, error: null, data: null });
  const [inspectReport, setInspectReport] = useState<{
    loading: boolean;
    error: string | null;
    data: Report | null;
  }>({ loading: false, error: null, data: null });
  const [uploaded, setUploaded] = useState<{ name: string; file: File; report: Report } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [adding, setAdding] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const library = evaluations.data ?? [];
  const selectedSummaries = useMemo(() => {
    const byId = new Map(library.map((item) => [item.id, item]));
    return selected.flatMap((id) => {
      const item = byId.get(id);
      return item ? [item] : [];
    });
  }, [library, selected]);

  useEffect(() => {
    if (seeded.current || evaluations.data == null) return;
    seeded.current = true;
    const known = new Set(evaluations.data.map((item) => item.id));
    setSelected(parseEvalsParam(searchParams.get("evals")).filter((id) => known.has(id)));
  }, [evaluations.data, searchParams]);

  useEffect(() => {
    let alive = true;
    setPairs(null);
    setPairsError(null);
    if (selected.length < 2) {
      setPairsLoading(false);
      return () => { alive = false; };
    }

    setPairsLoading(true);
    Promise.all(
      planPairs(selected).map((pair) =>
        api.compareEvaluations(pair.baseline, pair.challenger, intervention)
          .then((result) => ({ challenger: pair.challenger, result })),
      ),
    )
      .then((next) => { if (alive) setPairs(next); })
      .catch((error) => { if (alive) setPairsError(messageOf(error)); })
      .finally(() => { if (alive) setPairsLoading(false); });

    return () => { alive = false; };
  }, [selected, intervention]);

  useEffect(() => {
    let alive = true;
    setReports({});
    setReportsError(null);
    if (selected.length === 0) {
      setReportsLoading(false);
      return () => { alive = false; };
    }

    setReportsLoading(true);
    Promise.all(
      selected.map((id) => api.getEvaluationReport(id).then((report) => [id, report] as const)),
    )
      .then((entries) => { if (alive) setReports(Object.fromEntries(entries)); })
      .catch((error) => { if (alive) setReportsError(messageOf(error)); })
      .finally(() => { if (alive) setReportsLoading(false); });

    return () => { alive = false; };
  }, [selected]);

  const inspectedIsSelected = inspected != null && selected.includes(inspected);

  useEffect(() => {
    let alive = true;
    setInspectReport({ loading: false, error: null, data: null });
    if (!inspected || inspectedIsSelected) return () => { alive = false; };

    setInspectReport({ loading: true, error: null, data: null });
    api.getEvaluationReport(inspected)
      .then((data) => { if (alive) setInspectReport({ loading: false, error: null, data }); })
      .catch((error) => {
        if (alive) setInspectReport({ loading: false, error: messageOf(error), data: null });
      });
    return () => { alive = false; };
  }, [inspected, inspectedIsSelected]);

  useEffect(() => {
    let alive = true;
    setDiagnostics({ loading: false, error: null, data: null });
    if (!inspected) return () => { alive = false; };

    setDiagnostics({ loading: true, error: null, data: null });
    api.evaluationDiagnostics(inspected)
      .then((data) => { if (alive) setDiagnostics({ loading: false, error: null, data }); })
      .catch((error) => {
        if (alive) setDiagnostics({ loading: false, error: messageOf(error), data: null });
      });
    return () => { alive = false; };
  }, [inspected]);

  const summary = pairs ? driftSummary(pairs) : null;
  const exportReady = selected.length >= 2 && pairs != null && !pairsLoading;
  const forkItems = selected.length === 2
    ? selected.map((id) => library.find((item) => item.id === id))
    : [];
  const inspectedItem = inspected ? library.find((item) => item.id === inspected) : undefined;
  const activeInspectReport = inspectedIsSelected ? reports[inspected!] ?? null : inspectReport.data;
  const inspectReportLoading = inspectedIsSelected ? reportsLoading : inspectReport.loading;
  const inspectReportError = inspectedIsSelected ? reportsError : inspectReport.error;

  const metricGroups = useMemo(() => {
    const series = (valueFor: (report: Report) => number | null) =>
      selectedSummaries.map((item, index) => ({
        id: item.id,
        label: shortModel(item.model),
        color: COMPARE_PALETTE[index % COMPARE_PALETTE.length],
        value: reports[item.id] ? valueFor(reports[item.id]) : null,
      }));

    if (metric === "reliability" || metric === "average") {
      const keys = [...new Set(
        selected.flatMap((id) => reports[id]?.categories.map((category) => category.key) ?? []),
      )];
      return keys.map((key) => ({
        key,
        label: conflictLabel(key),
        series: series((report) => {
          const category = report.categories.find((candidate) => candidate.key === key);
          if (!category) return null;
          return metric === "reliability" ? category.pass_k_rate : category.mean_rate;
        }),
      }));
    }

    const axis = metric === "accuracy"
      ? "accuracy_rate"
      : metric === "provenance"
        ? "provenance_rate"
        : "refusal_rate";
    return [{
      key: "overall",
      label: COMPARE_COPY.metricOverall,
      series: series((report) => report.axes[axis]),
    }];
  }, [metric, reports, selected, selectedSummaries]);

  const exportComparison = (format: "html" | "json") => {
    if (!pairs) return;
    downloadComparison({
      generated_at: new Date().toISOString(),
      intervention,
      evaluations: selectedSummaries,
      pairs,
    }, format);
  };

  const pickFile = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    try {
      const report = await api.uploadReport(file);
      setUploaded({ name: file.name, file, report });
    } catch (error) {
      toast.error(COMPARE_COPY.importFailed(messageOf(error)));
    } finally {
      setUploading(false);
    }
  };

  const addUpload = async () => {
    if (!uploaded) return;
    setAdding(true);
    try {
      await api.importEvaluation(uploaded.file);
      evaluations.reload();
      setUploaded(null);
    } catch (error) {
      toast.error(COMPARE_COPY.importFailed(messageOf(error)));
    } finally {
      setAdding(false);
    }
  };

  const importSlot = (
    <div>
      <input
        ref={fileRef}
        type="file"
        accept=".eval"
        className="hidden"
        aria-label={COMPARE_COPY.importButton}
        onChange={(event) => {
          void pickFile(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <Button
        variant="outline"
        size="sm"
        className="w-full"
        disabled={uploading}
        onClick={() => fileRef.current?.click()}
      >
        {COMPARE_COPY.importButton}
      </Button>
      <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
        {COMPARE_COPY.importHint}
      </p>
    </div>
  );

  return (
    <div className="grid gap-4 lg:grid-cols-4">
      <div className="space-y-3 lg:col-span-1">
        {evaluations.loading && <Skeleton className="h-40 w-full" />}
        {evaluations.error && (
          <Alert variant="destructive">
            <AlertDescription>
              {COMPARE_COPY.loadFailed(COMPARE_COPY.rail, evaluations.error)}
            </AlertDescription>
          </Alert>
        )}
        <RunPicker
          evaluations={library}
          selected={selected}
          onToggle={setSelected}
          onInspect={setInspected}
          importSlot={importSlot}
        />
      </div>

      <div className="space-y-4 lg:col-span-3">
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <SectionLabel>{COMPARE_COPY.intervention}</SectionLabel>
            <Select
              value={intervention}
              onValueChange={(value) => setIntervention(value as ComparisonIntervention)}
              items={INTERVENTIONS}
            >
              <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
              <SelectContent>
                {INTERVENTIONS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" size="sm" disabled={!exportReady} onClick={() => exportComparison("html")}>
            {COMPARE_COPY.exportHtml}
          </Button>
          <Button variant="outline" size="sm" disabled={!exportReady} onClick={() => exportComparison("json")}>
            {COMPARE_COPY.exportJson}
          </Button>
          {forkItems.length === 2 && forkItems[0] && forkItems[1] && (
            <Button
              className="sm:ml-auto"
              variant="outline"
              size="sm"
              nativeButton={false}
              render={
                <Link
                  to={`/compare?tab=experiments&baseline=${encodeURIComponent(forkItems[0].model)}&challenger=${encodeURIComponent(forkItems[1].model)}&org=${encodeURIComponent(forkItems[0].org ?? "toy")}`}
                />
              }
            >
              {COMPARE_COPY.forkExperiment}
            </Button>
          )}
        </div>

        {selected.length < 2 ? (
          <Card className="border-primary/35 p-4 text-sm text-muted-foreground">
            {COMPARE_COPY.needTwo}
          </Card>
        ) : pairsLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : pairsError ? (
          <Alert variant="destructive">
            <AlertDescription>
              {COMPARE_COPY.loadFailed(COMPARE_COPY.title, pairsError)}
            </AlertDescription>
          </Alert>
        ) : summary ? (
          <Card
            className={cn(
              "p-4",
              summary.compatible
                ? "border-verdict-reliable/45 text-verdict-reliable"
                : "border-verdict-inconsistent/55 text-verdict-inconsistent",
            )}
          >
            <div className="font-semibold">
              {summary.compatible ? COMPARE_COPY.controlled : COMPARE_COPY.drift}
            </div>
            <div className="text-xs text-muted-foreground">
              {summary.compatible
                ? COMPARE_COPY.controlledDetail(intervention, summary.changed.join(", "))
                : summary.unexpectedByChallenger.map(({ challenger, dims }) => (
                    <div key={challenger}>{COMPARE_COPY.driftDetail(challenger, dims.join(", "))}</div>
                  ))}
            </div>
          </Card>
        ) : null}

        <Card className="p-4">
          <div className="mb-3">
            <SectionLabel>{COMPARE_COPY.gapPanel}</SectionLabel>
            <p className="text-[11px] text-faint">{COMPARE_COPY.gapPanelSub}</p>
          </div>
          <div className="space-y-3">
            {selectedSummaries.map((item, index) => (
              <div key={item.id} className="flex items-center gap-3">
                <span
                  className="w-36 shrink-0 truncate text-xs font-medium"
                  style={{ color: COMPARE_PALETTE[index % COMPARE_PALETTE.length] }}
                  title={item.id}
                >
                  {shortModel(item.model)}
                </span>
                <GapBar passK={item.pass_k_rate ?? 0} mean={item.mean_rate ?? 0} k={item.epochs} />
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <Tabs value={metric} onValueChange={(value) => setMetric(value as Metric)}>
            <TabsList variant="line" className="mb-4 flex-wrap">
              {METRICS.map((key) => (
                <TabsTrigger key={key} value={key}>{COMPARE_COPY.metricTabs[key]}</TabsTrigger>
              ))}
            </TabsList>
            {METRICS.map((key) => (
              <TabsContent key={key} value={key}>
                <SectionLabel>
                  {key === "reliability" || key === "average"
                    ? COMPARE_COPY.metricByCategory
                    : COMPARE_COPY.metricOverall}
                </SectionLabel>
                {reportsLoading && <Skeleton className="h-28 w-full" />}
                {reportsError && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      {COMPARE_COPY.loadFailed(COMPARE_COPY.metricTabs[key], reportsError)}
                    </AlertDescription>
                  </Alert>
                )}
                {!reportsLoading && !reportsError && <CategoryBars groups={metricGroups} />}
              </TabsContent>
            ))}
          </Tabs>
        </Card>

        {selected.length === 2 && pairs?.[0] && (() => {
          const result = pairs[0].result;
          const rows = [...result.categories, { ...result.overall, key: "OVERALL" }];
          return (
            <Card className="p-0">
              <div className="px-4 pt-4">
                <SectionLabel>{COMPARE_COPY.significance}</SectionLabel>
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="text-[10px] uppercase tracking-[0.15em]">
                      {COMPARE_COPY.significanceCols.category}
                    </TableHead>
                    <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">
                      {COMPARE_COPY.significanceCols.matched}
                    </TableHead>
                    <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">
                      {COMPARE_COPY.significanceCols.aWins}
                    </TableHead>
                    <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">
                      {COMPARE_COPY.significanceCols.bWins}
                    </TableHead>
                    <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">
                      {COMPARE_COPY.significanceCols.p}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.key} className={cn("text-xs", row.key === "OVERALL" && "font-bold")}>
                      <TableCell>{conflictLabel(row.key)}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.matched}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.a_wins}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.b_wins}</TableCell>
                      <TableCell className="text-right tabular-nums">{pValue(row.p_value)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {result.overall.dropped.length > 0 && (
                <div className="border-t border-border px-4 py-2 text-[10px] text-muted-foreground">
                  {COMPARE_COPY.unmatched(result.overall.dropped.length, result.overall.dropped.join(", "))}
                </div>
              )}
            </Card>
          );
        })()}

        {uploaded && (
          <Card className="p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <SectionLabel>{COMPARE_COPY.importInspecting(uploaded.name)}</SectionLabel>
              <div className="flex gap-2">
                <Button variant="outline" size="xs" onClick={() => void addUpload()} disabled={adding}>
                  {adding ? COMPARE_COPY.importAdding : COMPARE_COPY.importAdd}
                </Button>
                <Button variant="ghost" size="xs" onClick={() => setUploaded(null)}>
                  {COMPARE_COPY.importClose}
                </Button>
              </div>
            </div>
            <Scorecard key={uploaded.name} report={uploaded.report} />
          </Card>
        )}

        {inspectedItem && (
          <div className="space-y-4">
            <EvaluationDetail item={inspectedItem} diagnostics={diagnostics} />
            {inspectReportLoading && <Skeleton className="h-60 w-full" />}
            {inspectReportError && (
              <Alert variant="destructive">
                <AlertDescription>
                  {COMPARE_COPY.loadFailed(COMPARE_COPY.detail, inspectReportError)}
                </AlertDescription>
              </Alert>
            )}
            {activeInspectReport && (
              <Card className="p-4">
                <Scorecard key={inspectedItem.id} report={activeInspectReport} />
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
