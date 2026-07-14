import { useRef, useState } from "react";
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
import type { LogMeta, Report } from "@/types";
import { conflictLabel, engineLabel } from "../copy";

function rowLabel(m: LogMeta) {
  return `${shortModel(m.model)}${m.grader ? ` / ${shortModel(m.grader)}` : ""}`;
}

function DiffTable({ a, b }: { a: Report; b: Report }) {
  const order = ["none", "resolvable", "unresolvable", "void"];
  const da = Object.fromEntries(a.categories.map((c) => [c.key, c.pass_k_rate]));
  const db = Object.fromEntries(b.categories.map((c) => [c.key, c.pass_k_rate]));
  const rows = order.filter((k) => k in da || k in db).map((k) => ({ k, a: da[k], b: db[k] }));
  rows.push({ k: "OVERALL", a: a.overall.pass_k_rate, b: b.overall.pass_k_rate });
  return (
    <Panel title="delta — reliability by question type (B − A)" bodyClassName="p-0">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="text-[10px] uppercase tracking-[0.15em]">question type</TableHead>
            <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">A · {shortModel(a.header.model)}</TableHead>
            <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">B · {shortModel(b.header.model)}</TableHead>
            <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">Δ</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => {
            const delta = r.a != null && r.b != null ? Math.round((r.b - r.a) * 100) : null;
            return (
              <TableRow key={r.k} className={cn("text-xs", r.k === "OVERALL" && "font-bold")}>
                <TableCell>{r.k === "OVERALL" ? "OVERALL" : conflictLabel(r.k)}</TableCell>
                <TableCell className="text-right tabular-nums">{pct(r.a)}</TableCell>
                <TableCell className="text-right tabular-nums">{pct(r.b)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {delta === null ? "" : delta === 0 ? "±0" : `${delta > 0 ? "+" : ""}${delta} pts`}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Panel>
  );
}

export default function Results() {
  const logs = useAsync(() => api.listLogs(), []);
  const [selA, setSelA] = useState("");
  const [selB, setSelB] = useState("");
  const [compare, setCompare] = useState(false);
  const [uploaded, setUploaded] = useState<{ name: string; report: Report } | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // newest first — real runs shouldn't lose the default slot to pinned demos
  const list = [...(logs.data ?? [])].sort((x, y) => y.created.localeCompare(x.created));
  const idA = selA || list[0]?.id || "";
  const idB = selB || list.find((l) => l.id !== idA)?.id || "";
  const runA = list.find((l) => l.id === idA);

  const compareItems = list.map((l) => ({
    value: l.id,
    label: `${rowLabel(l)} · ${l.created.slice(0, 10)}`,
  }));

  const repA = useAsync(
    () => (idA && !uploaded ? api.getReport(idA) : Promise.resolve(null)),
    [idA, uploaded],
  );
  const repB = useAsync(
    () => (compare && idB ? api.getReport(idB) : Promise.resolve(null)),
    [idB, compare],
  );

  function onUpload(f: File | undefined) {
    if (!f) return;
    setUploadErr(null);
    api
      .uploadReport(f)
      .then((report) => setUploaded({ name: f.name, report }))
      .catch((e) => setUploadErr(String(e?.message ?? e)));
  }

  return (
    <div className="space-y-4">
      <ViewHeader
        cmd="tessera report --inspect"
        desc="read a run down to the failed transcripts — a question counts only if it was right on every repeat (pass^k)"
      />

      {logs.error && <ErrLine msg={logs.error} />}
      {uploadErr && <ErrLine msg={`upload failed: ${uploadErr}`} />}

      <div className="grid gap-4 lg:grid-cols-4">
        {/* picker */}
        <div className="space-y-4 lg:col-span-1">
          <Panel
            title={`runs (${list.length})`}
            right={
              <button
                onClick={() => { setCompare((c) => !c); setUploaded(null); }}
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
            {logs.loading && <div className="p-3"><Skeleton className="h-16 w-full" /></div>}
            <div className="max-h-[420px] overflow-auto">
              {list.map((m) => {
                const active = !uploaded && m.id === idA;
                const isB = compare && m.id === idB;
                return (
                  <button
                    key={m.id}
                    onClick={() => { setSelA(m.id); setUploaded(null); }}
                    className={cn(
                      "block w-full border-b border-border px-3 py-2 text-left text-xs last:border-b-0",
                      active ? "bg-foreground text-background" : "hover:bg-muted",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-bold">
                        {m.source === "examples" ? "★ " : ""}{rowLabel(m)}
                      </span>
                      {isB && <span className="shrink-0 border border-current px-1 text-[9px]">B</span>}
                    </div>
                    <div className={cn("flex justify-between text-[10px]", active ? "text-background/70" : "text-muted-foreground")}>
                      <span>{engineLabel(m.engine)}{m.org ? ` · ${m.org}` : ""} · {m.k} repeats</span>
                      <span>{m.created.slice(0, 10)}</span>
                    </div>
                  </button>
                );
              })}
              {!logs.loading && list.length === 0 && (
                <div className="p-3 text-xs text-muted-foreground">no .eval logs found</div>
              )}
            </div>
          </Panel>

          <Panel title="local file">
            <input
              ref={fileRef}
              type="file"
              accept=".eval"
              className="hidden"
              onChange={(e) => {
                onUpload(e.target.files?.[0]);
                e.target.value = ""; // allow re-selecting the same file
              }}
            />
            <Button variant="outline" size="sm" className="w-full" onClick={() => fileRef.current?.click()}>
              inspect a local .eval…
            </Button>
            <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
              renders a scorecard from any inspect_ai log without saving it
            </p>
          </Panel>
        </div>

        {/* report(s) */}
        <div className="space-y-4 lg:col-span-3">
          {uploaded ? (
            <Panel
              title={`local — ${uploaded.name}`}
              right={
                <Button variant="ghost" size="xs" onClick={() => setUploaded(null)}>✕ close</Button>
              }
            >
              <Scorecard key={uploaded.name} report={uploaded.report} />
            </Panel>
          ) : compare ? (
            <>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <SectionLabel>run A (pick from the list)</SectionLabel>
                  <div className="border border-border bg-card px-2 py-1.5 text-xs">
                    {runA ? rowLabel(runA) : "—"}
                  </div>
                </div>
                <div>
                  <SectionLabel>run B</SectionLabel>
                  <Select value={idB} onValueChange={(v) => setSelB(v as string)} items={compareItems}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {compareItems.map((l) => (
                        <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {repA.data && repB.data && <DiffTable a={repA.data} b={repB.data} />}
              <div className="grid gap-4 xl:grid-cols-2">
                <Panel title="run A">
                  {repA.loading ? <Skeleton className="h-40 w-full" /> : repA.error ? <ErrLine msg={repA.error} /> : repA.data && <Scorecard key={idA} report={repA.data} />}
                </Panel>
                <Panel title="run B">
                  {repB.loading ? (
                    <Skeleton className="h-40 w-full" />
                  ) : repB.error ? (
                    <ErrLine msg={repB.error} />
                  ) : repB.data ? (
                    <Scorecard key={idB} report={repB.data} />
                  ) : (
                    <div className="text-xs text-muted-foreground">pick run B above</div>
                  )}
                </Panel>
              </div>
            </>
          ) : (
            <Panel title="scorecard">
              {repA.loading ? (
                <Skeleton className="h-60 w-full" />
              ) : repA.error ? (
                <ErrLine msg={repA.error} />
              ) : repA.data ? (
                <Scorecard key={idA} report={repA.data} />
              ) : (
                <div className="text-xs text-muted-foreground">select a run on the left</div>
              )}
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
