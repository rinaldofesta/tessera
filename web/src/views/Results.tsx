import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import { Scorecard } from "@/components/Scorecard";
import { ErrLine, Panel, SectionLabel, ViewHeader } from "@/components/term";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useAsync } from "@/hooks";
import { pct, shortModel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  ComparisonIntervention, ComparisonResult, EvaluationSummary, Report,
} from "@/types";
import { conflictLabel, engineLabel } from "../copy";

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

function rowLabel(item: EvaluationSummary) {
  return `${shortModel(item.model)}${item.grader ? ` / ${shortModel(item.grader)}` : ""}`;
}

function pValue(value: number): string {
  return value < 0.0001 ? "< 0.0001" : value.toFixed(4);
}

function ComparisonPanel({ result, a, b }: {
  result: ComparisonResult; a: EvaluationSummary; b: EvaluationSummary;
}) {
  const rows = [
    ...result.categories.map((row) => ({ ...row, label: conflictLabel(row.key) })),
    { ...result.overall, key: "OVERALL", label: "OVERALL" },
  ];
  return (
    <div className="space-y-3">
      <div className={cn(
        "border px-3 py-2 text-xs",
        result.compatible ? "border-[var(--verdict-reliable)]/50" : "border-[var(--verdict-unreliable)]/60",
      )}>
        <div className="font-bold">
          {result.compatible ? "Controlled comparison" : "Protocol drift detected"}
        </div>
        <div className="mt-1 text-muted-foreground">
          Declared intervention: {result.intervention}. Changed: {result.changed_dimensions.join(", ") || "none"}.
          {result.unexpected_dimensions.length > 0 && (
            <> Unexpected: {result.unexpected_dimensions.join(", ")}.</>
          )}
        </div>
      </div>

      <Panel title="paired outcomes — probe × repeat" bodyClassName="p-0">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="text-[10px] uppercase tracking-[0.15em]">question type</TableHead>
              <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">paired n</TableHead>
              <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">A only passes</TableHead>
              <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">B only passes</TableHead>
              <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">exact p</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.key} className={cn("text-xs", row.key === "OVERALL" && "font-bold")}>
                <TableCell>{row.label}</TableCell>
                <TableCell className="text-right tabular-nums">{row.matched}</TableCell>
                <TableCell className="text-right tabular-nums">{row.a_wins}</TableCell>
                <TableCell className="text-right tabular-nums">{row.b_wins}</TableCell>
                <TableCell className="text-right tabular-nums">{pValue(row.p_value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {result.overall.dropped.length > 0 && (
          <div className="border-t border-border px-3 py-2 text-[10px] text-muted-foreground">
            {result.overall.dropped.length} unmatched observation(s): {result.overall.dropped.join(", ")}
          </div>
        )}
      </Panel>

      <div className="grid gap-3 md:grid-cols-2">
        {(["a", "b"] as const).map((arm) => {
          const item = arm === "a" ? a : b;
          const diagnostics = result.diagnostics[arm];
          return (
            <Panel key={arm} title={`${arm.toUpperCase()} friction — ${shortModel(item.model)}`}>
              {diagnostics.length === 0 ? (
                <p className="text-xs text-muted-foreground">no recorded failure signatures</p>
              ) : (
                <div className="space-y-1 text-xs">
                  {diagnostics.slice(0, 8).map((entry) => (
                    <div key={`${entry.kind}:${entry.signature}`} className="flex justify-between gap-3">
                      <span className="truncate">{entry.kind.replace(/_/g, " ")} · {entry.signature}</span>
                      <span className="tabular-nums text-muted-foreground">×{entry.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          );
        })}
      </div>
    </div>
  );
}

function ReceiptPanel({ item }: { item: EvaluationSummary }) {
  const receipt = item.receipt;
  const usage = receipt.usage;
  const cost = usage.billed_cost;
  return (
    <Panel title="run receipt">
      <dl className="grid gap-x-4 gap-y-2 text-xs sm:grid-cols-2">
        <div>
          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">protocol fingerprint</dt>
          <dd className="truncate font-mono" title={receipt.protocol_hash}>{receipt.protocol_hash.slice(0, 16)}…</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">execution fingerprint</dt>
          <dd className="truncate font-mono" title={receipt.execution_hash}>{receipt.execution_hash.slice(0, 16)}…</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">effective model</dt>
          <dd>{receipt.runtime.effective_models.join(", ") || "not reported"}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">runtime</dt>
          <dd>{receipt.runtime.inspect_ai_version ?? "unknown"} · tessera {receipt.runtime.tessera_version ?? "unknown"}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">usage</dt>
          <dd>{usage.total_tokens.toLocaleString()} tokens{cost == null ? "" : ` · $${cost.toFixed(4)}`}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">duration</dt>
          <dd>{receipt.timing.duration_seconds == null ? "not reported" : `${receipt.timing.duration_seconds.toFixed(1)}s`}</dd>
        </div>
      </dl>
    </Panel>
  );
}

export default function Results() {
  const evaluations = useAsync(() => api.listEvaluations(), []);
  const [selA, setSelA] = useState("");
  const [selB, setSelB] = useState("");
  const [compare, setCompare] = useState(false);
  const [intervention, setIntervention] = useState<ComparisonIntervention>("model");
  const [uploaded, setUploaded] = useState<{ name: string; file: File; report: Report } | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const list = evaluations.data ?? [];
  const idA = selA || list[0]?.id || "";
  const idB = selB || list.find((item) => item.id !== idA)?.id || "";
  const itemA = list.find((item) => item.id === idA);
  const itemB = list.find((item) => item.id === idB);
  const selectItems = list.map((item) => ({
    value: item.id, label: `${rowLabel(item)} · ${item.created_at.slice(0, 10)}`,
  }));

  const repA = useAsync(
    () => (idA && !uploaded ? api.getEvaluationReport(idA) : Promise.resolve(null)),
    [idA, uploaded],
  );
  const repB = useAsync(
    () => (compare && idB ? api.getEvaluationReport(idB) : Promise.resolve(null)),
    [idB, compare],
  );
  const comparison = useAsync<ComparisonResult | null>(
    () => (compare && idA && idB
      ? api.compareEvaluations(idA, idB, intervention)
      : Promise.resolve(null)),
    [compare, idA, idB, intervention],
  );
  const diagnostics = useAsync(
    () => (idA && !uploaded ? api.evaluationDiagnostics(idA) : Promise.resolve([])),
    [idA, uploaded],
  );

  function onUpload(file: File | undefined) {
    if (!file) return;
    setUploadErr(null);
    api.uploadReport(file)
      .then((report) => setUploaded({ name: file.name, file, report }))
      .catch((error) => setUploadErr(String(error?.message ?? error)));
  }

  async function saveUpload() {
    if (!uploaded) return;
    setSaving(true);
    setUploadErr(null);
    try {
      const saved = await api.importEvaluation(uploaded.file);
      setSelA(saved.id);
      setUploaded(null);
      evaluations.reload();
    } catch (error) {
      setUploadErr(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <ViewHeader
        cmd="tessera evaluations"
        desc="indexed evidence, immutable run receipts, and paired comparisons that surface protocol drift"
      />
      {evaluations.error && <ErrLine msg={evaluations.error} />}
      {uploadErr && <ErrLine msg={`upload failed: ${uploadErr}`} />}

      <div className="grid gap-4 lg:grid-cols-4">
        <div className="space-y-4 lg:col-span-1">
          <Panel
            title={`evaluation library (${list.length})`}
            right={
              <button
                onClick={() => { setCompare((current) => !current); setUploaded(null); }}
                className={cn(
                  "px-1 text-[10px] uppercase tracking-[0.15em]",
                  compare ? "bg-foreground font-bold text-background" : "text-muted-foreground hover:text-foreground",
                )}
              >
                compare:{compare ? "on" : "off"}
              </button>
            }
            bodyClassName="p-0"
          >
            {evaluations.loading && <div className="p-3"><Skeleton className="h-16 w-full" /></div>}
            <div className="max-h-[440px] overflow-auto">
              {list.map((item) => {
                const active = !uploaded && item.id === idA;
                const isB = compare && item.id === idB;
                return (
                  <button
                    key={item.id}
                    onClick={() => { setSelA(item.id); setUploaded(null); }}
                    className={cn(
                      "block w-full border-b border-border px-3 py-2 text-left text-xs last:border-b-0",
                      active ? "bg-foreground text-background" : "hover:bg-muted",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-bold">{item.kind === "pinned" ? "★ " : ""}{rowLabel(item)}</span>
                      {isB && <span className="shrink-0 border border-current px-1 text-[9px]">B</span>}
                    </div>
                    <div className={cn("flex justify-between text-[10px]", active ? "text-background/70" : "text-muted-foreground")}>
                      <span>{item.kind} · {engineLabel(item.engine)} · {item.epochs} repeats</span>
                      <span>{pct(item.pass_k_rate)}</span>
                    </div>
                  </button>
                );
              })}
              {!evaluations.loading && list.length === 0 && (
                <div className="p-3 text-xs text-muted-foreground">no evaluations indexed</div>
              )}
            </div>
          </Panel>

          <Panel title="local .eval">
            <input
              ref={fileRef} type="file" accept=".eval" className="hidden"
              onChange={(event) => {
                onUpload(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
            <Button variant="outline" size="sm" className="w-full" onClick={() => fileRef.current?.click()}>
              inspect without saving…
            </Button>
            <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
              inspect once, then explicitly add it to the evaluation library
            </p>
          </Panel>
        </div>

        <div className="space-y-4 lg:col-span-3">
          {uploaded ? (
            <Panel
              title={`local — ${uploaded.name}`}
              right={<div className="flex gap-2">
                <Button variant="outline" size="xs" onClick={saveUpload} disabled={saving}>
                  {saving ? "adding…" : "add to library"}
                </Button>
                <Button variant="ghost" size="xs" onClick={() => setUploaded(null)}>✕ close</Button>
              </div>}
            >
              <Scorecard key={uploaded.name} report={uploaded.report} />
            </Panel>
          ) : compare ? (
            <>
              <div className="grid gap-2 md:grid-cols-3">
                <div>
                  <SectionLabel>run A</SectionLabel>
                  <div className="h-8 border border-border bg-card px-2 py-1.5 text-xs">
                    {itemA ? rowLabel(itemA) : "—"}
                  </div>
                </div>
                <div>
                  <SectionLabel>run B</SectionLabel>
                  <Select value={idB} onValueChange={(value) => setSelB(value as string)} items={selectItems}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>{selectItems.map((item) => (
                      <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                    ))}</SelectContent>
                  </Select>
                </div>
                <div>
                  <SectionLabel>intended change</SectionLabel>
                  <Select value={intervention} onValueChange={(value) => setIntervention(value as ComparisonIntervention)} items={INTERVENTIONS}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>{INTERVENTIONS.map((item) => (
                      <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                    ))}</SelectContent>
                  </Select>
                </div>
              </div>

              {comparison.loading && <Skeleton className="h-40 w-full" />}
              {comparison.error && <ErrLine msg={comparison.error} />}
              {comparison.data && itemA && itemB && (
                <ComparisonPanel result={comparison.data} a={itemA} b={itemB} />
              )}
              {itemA && itemB && (
                <Button
                  variant="outline" nativeButton={false}
                  render={<Link to={`/experiments?baseline=${encodeURIComponent(itemA.model)}&challenger=${encodeURIComponent(itemB.model)}&org=${encodeURIComponent(itemA.org ?? "toy")}`} />}
                >
                  fork as controlled experiment
                </Button>
              )}
              <div className="grid gap-4 xl:grid-cols-2">
                <Panel title="run A">
                  {repA.loading ? <Skeleton className="h-40 w-full" /> : repA.error ? <ErrLine msg={repA.error} /> : repA.data && <Scorecard key={idA} report={repA.data} />}
                </Panel>
                <Panel title="run B">
                  {repB.loading ? <Skeleton className="h-40 w-full" /> : repB.error ? <ErrLine msg={repB.error} /> : repB.data && <Scorecard key={idB} report={repB.data} />}
                </Panel>
              </div>
            </>
          ) : (
            <>
              {itemA && <ReceiptPanel item={itemA} />}
              {itemA && (
                <Panel title="failure signatures">
                  {diagnostics.loading ? <Skeleton className="h-12 w-full" /> : diagnostics.error ? (
                    <ErrLine msg={diagnostics.error} />
                  ) : diagnostics.data?.length ? (
                    <div className="grid gap-1 text-xs sm:grid-cols-2">
                      {diagnostics.data.map((entry) => (
                        <div key={`${entry.kind}:${entry.signature}`} className="flex justify-between gap-3 border-b border-border py-1">
                          <span className="truncate">{entry.kind.replace(/_/g, " ")} · {entry.signature}</span>
                          <span className="tabular-nums text-muted-foreground">×{entry.count}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">no recorded failure signatures</p>
                  )}
                </Panel>
              )}
              <Panel title="scorecard">
                {repA.loading ? <Skeleton className="h-60 w-full" /> : repA.error ? <ErrLine msg={repA.error} /> : repA.data ? <Scorecard key={idA} report={repA.data} /> : (
                  <div className="text-xs text-muted-foreground">select an evaluation on the left</div>
                )}
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
