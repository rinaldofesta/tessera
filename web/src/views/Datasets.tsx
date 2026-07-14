import { useEffect, useRef, useState } from "react";
import { api } from "@/api";
import { ScenarioCards } from "@/components/ScenarioCards";
import { ErrLine, Panel, SectionLabel, ViewHeader } from "@/components/term";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldLabel, ValidationErrors } from "@/components/form";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAsync } from "@/hooks";
import { cn } from "@/lib/utils";
import type { Artifacts, Blueprint, Claim, ProbeDef, ValidationResult } from "@/types";
import { CONFLICT } from "../copy";

// editor rows carry a stable uid so removable rows don't recycle React state
type ClaimRow = Claim & { _uid: string };
type ProbeRow = ProbeDef & { _uid: string };
type BpRows = { claims: ClaimRow[]; probes: ProbeRow[] };

const uid = () => crypto.randomUUID();
const withUids = (b: Blueprint): BpRows => ({
  claims: b.claims.map((c) => ({ ...c, _uid: uid() })),
  probes: (b.probes ?? []).map((p) => ({ ...p, _uid: uid() })),
});
const stripUids = (b: BpRows): Blueprint => ({
  claims: b.claims.map(({ _uid, ...c }) => c),
  probes: b.probes.map(({ _uid, ...p }) => p),
});

const EMPTY: BpRows = { claims: [], probes: [] };
const newClaim = (): ClaimRow => ({ _uid: uid(), claim_id: "", subject: "", predicate: "", value: "", silo: "crm", render: { as: "field" } });
const newProbe = (): ProbeRow => ({ _uid: uid(), probe_id: "", question: "", references: [], conflict_type: "none", expected_behavior: "answer", expected_answer: "", expected_sources: [] });
const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

const SILOS = [
  { value: "crm", label: "crm record — structured field" },
  { value: "docs", label: "document — written prose" },
];
const CONFLICT_TYPES = ["none", "resolvable", "unresolvable", "void"].map((value) => ({
  value,
  label: `${CONFLICT[value].label} (${value})`,
}));
const RULES = [
  { value: "", label: "— pick a tiebreaker —" },
  { value: "recency_wins", label: "newer wins (recency_wins)" },
  { value: "authority_wins", label: "more authoritative wins (authority_wins)" },
];

const tabCls =
  "rounded-none px-2.5 py-1 text-xs data-[state=active]:bg-foreground data-[state=active]:text-background data-[active]:bg-foreground data-[active]:text-background";

export default function Datasets() {
  const list = useAsync(() => api.listBlueprints(), []);
  const [selected, setSelected] = useState<string>("");
  const [isNew, setIsNew] = useState(false);
  const [bp, setBp] = useState<BpRows>(EMPTY);
  const [advanced, setAdvanced] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [loadingBp, setLoadingBp] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [preview, setPreview] = useState<Artifacts | null>(null);
  const [previewErr, setPreviewErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string>("");
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [newId, setNewId] = useState("");
  const [pending, setPending] = useState<{ kind: "load"; id: string } | { kind: "new" } | null>(null);
  const loadSeq = useRef(0);

  const ids = list.data ?? [];
  useEffect(() => {
    if (!selected && !isNew && ids.length) load(ids[0].id);
  }, [list.data]); // eslint-disable-line react-hooks/exhaustive-deps

  function load(id: string) {
    const prev = selected;
    const seq = ++loadSeq.current;
    setSelected(id);
    setIsNew(false);
    setLoadingBp(true);
    setMsg("");
    setPreview(null);
    api
      .getBlueprint(id)
      .then((b) => {
        if (loadSeq.current !== seq) return; // a newer load won
        setBp(withUids(b));
        setDirty(false);
      })
      .catch((e) => {
        if (loadSeq.current !== seq) return;
        setMsg(`load failed: ${e.message}`);
        setSelected(prev); // keep editor and selection consistent
      })
      .finally(() => {
        if (loadSeq.current === seq) setLoadingBp(false);
      });
  }
  function doNew() {
    setSelected("");
    setIsNew(true);
    // starts empty, not a blank claim+probe pair — the simple view's own
    // "+ new scenario" CTA is the entry point for a fresh blueprint now
    setBp(EMPTY);
    setDirty(false);
    setPreview(null);
    setMsg("");
  }
  // unsaved edits are guarded by a confirm — a misclick must not discard work
  const requestLoad = (id: string) => (dirty ? setPending({ kind: "load", id }) : load(id));
  const requestNew = () => (dirty ? setPending({ kind: "new" }) : doNew());

  // live validation (debounced + stale-response guard)
  useEffect(() => {
    let alive = true;
    const t = setTimeout(() => {
      api
        .validateBlueprint(stripUids(bp))
        .then((v) => { if (alive) setValidation(v); })
        .catch(() => {
          if (alive)
            setValidation({ ok: false, errors: [{ location: "(api)", message: "validation request failed — backend unreachable?" }] });
        });
    }, 400);
    return () => { alive = false; clearTimeout(t); };
  }, [bp]);

  const touch = (fn: (b: BpRows) => BpRows) => {
    setDirty(true);
    setBp(fn);
  };
  const setClaim = (id: string, c: Partial<Claim>) =>
    touch((b) => ({ ...b, claims: b.claims.map((x) => (x._uid === id ? { ...x, ...c } : x)) }));
  const setProbe = (id: string, p: Partial<ProbeDef>) =>
    touch((b) => ({ ...b, probes: b.probes.map((x) => (x._uid === id ? { ...x, ...p } : x)) }));
  const removeClaim = (id: string) => touch((b) => ({ ...b, claims: b.claims.filter((x) => x._uid !== id) }));
  const removeProbe = (id: string) => touch((b) => ({ ...b, probes: b.probes.filter((x) => x._uid !== id) }));
  const addClaim = () => touch((b) => ({ ...b, claims: [...b.claims, newClaim()] }));
  const addProbe = () => touch((b) => ({ ...b, probes: [...b.probes, newProbe()] }));
  const insertScenario = (claims: Claim[], probe: ProbeDef) =>
    touch((b) => ({
      ...b,
      claims: [...b.claims, ...claims.map((c) => ({ ...c, _uid: uid() }))],
      probes: [...b.probes, { ...probe, _uid: uid() }],
    }));

  async function doPreview() {
    setPreviewErr(null);
    try {
      setPreview(await api.previewBlueprint(stripUids(bp)));
    } catch (e) {
      setPreview(null);
      setPreviewErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function save() {
    if (!selected) {
      setNewId("");
      setSaveErr(null);
      setSaveOpen(true);
      return;
    }
    try {
      await api.saveBlueprint(selected, stripUids(bp));
      setDirty(false);
      setMsg(`saved '${selected}'`);
      list.reload();
    } catch (e) {
      setMsg(`save failed: ${e instanceof Error ? e.message : e}`);
    }
  }
  async function saveAs() {
    try {
      await api.createBlueprint(newId, stripUids(bp));
      setSaveOpen(false);
      setSelected(newId);
      setIsNew(false);
      setDirty(false);
      setMsg(`created '${newId}'`);
      list.reload();
    } catch (e) {
      // keep the dialog (and the typed id) — show the error where the user is looking
      setSaveErr(e instanceof Error ? e.message : String(e));
    }
  }
  async function remove() {
    if (!selected) return;
    try {
      await api.deleteBlueprint(selected);
      setSelected("");
      setBp(EMPTY);
      setDirty(false);
      setPreview(null);
      list.reload();
    } catch (e) {
      setMsg(`delete failed: ${e instanceof Error ? e.message : e}`);
    }
  }

  const plain = stripUids(bp); // simple view + wizard only ever see the real Claim/ProbeDef shape

  return (
    <div className="space-y-4">
      <ViewHeader
        cmd="tessera blueprint edit"
        desc="author facts (claims) + test questions (probes) — validated and compiled live, nothing leaves your machine"
      />

      <div className="grid gap-4 lg:grid-cols-12">
        {/* blueprint list */}
        <div className="lg:col-span-2">
          <Panel
            title="blueprints"
            right={
              <button onClick={requestNew} className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground hover:text-foreground">
                + new
              </button>
            }
            bodyClassName="p-0"
          >
            {list.loading && <div className="p-3"><Skeleton className="h-12 w-full" /></div>}
            {list.error && <div className="p-2"><ErrLine msg={list.error} /></div>}
            {ids.map((b) => (
              <button
                key={b.id}
                onClick={() => requestLoad(b.id)}
                className={cn(
                  "block w-full border-b border-border px-3 py-2 text-left text-xs last:border-b-0",
                  selected === b.id ? "bg-foreground font-bold text-background" : "hover:bg-muted",
                )}
              >
                <div className="truncate">{b.id}{dirty && selected === b.id ? " *" : ""}</div>
                <div className={cn("text-[10px]", selected === b.id ? "text-background/70" : "text-muted-foreground")}>
                  {b.claims} facts · {b.probes} questions
                </div>
              </button>
            ))}
            {isNew && (
              <div className="border-b border-border bg-foreground px-3 py-2 text-xs font-bold text-background last:border-b-0">
                (unsaved{dirty ? " *" : ""})
              </div>
            )}
            {!list.loading && !list.error && ids.length === 0 && !isNew && (
              <div className="p-3 text-xs text-muted-foreground">no blueprints — [+ new] to start</div>
            )}
          </Panel>
        </div>

        {/* editor */}
        <div className="lg:col-span-7">
          <Panel
            title={`editor — ${selected || "(new)"}${dirty ? " *" : ""}`}
            right={
              <div className="flex items-center gap-1.5">
                {msg && <span className="mr-1 text-[10px] normal-case text-muted-foreground">{msg}</span>}
                <div className="flex overflow-hidden border border-border text-[10px] uppercase tracking-[0.15em]">
                  <button
                    onClick={() => setAdvanced(false)}
                    className={cn("px-2 py-1", !advanced ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground")}
                  >
                    simple
                  </button>
                  <button
                    onClick={() => setAdvanced(true)}
                    className={cn("border-l border-border px-2 py-1", advanced ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground")}
                  >
                    advanced
                  </button>
                </div>
                <Button size="xs" variant="outline" onClick={doPreview}>compile ▸</Button>
                <Button size="xs" onClick={save}>{selected ? "save" : "save as…"}</Button>
                {selected && (
                  <AlertDialog>
                    <AlertDialogTrigger render={<Button size="xs" variant="outline" />}>
                      delete
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>delete '{selected}'?</AlertDialogTitle>
                        <AlertDialogDescription>
                          removes the blueprint from the store. runs already recorded against it are kept.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={remove}>delete</AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </div>
            }
            bodyClassName="p-0"
          >
            {loadingBp ? (
              <div className="p-3"><Skeleton className="h-40 w-full" /></div>
            ) : !advanced ? (
              <ScenarioCards claims={plain.claims} probes={plain.probes ?? []} onInsert={insertScenario} />
            ) : (
              <Tabs defaultValue="claims">
                <TabsList className="h-9 w-full justify-start gap-1 rounded-none border-b border-border bg-transparent p-1">
                  <TabsTrigger value="claims" className={tabCls}>facts [{bp.claims.length}]</TabsTrigger>
                  <TabsTrigger value="probes" className={tabCls}>questions [{bp.probes.length}]</TabsTrigger>
                </TabsList>

                <TabsContent value="claims" className="space-y-2 p-3">
                  {bp.claims.map((c, i) => (
                    <div key={c._uid} className="border border-border p-2">
                      <div className="mb-1.5 flex items-center justify-between">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                          fact {i + 1}
                        </span>
                        <button
                          onClick={() => removeClaim(c._uid)}
                          className="text-[10px] text-muted-foreground hover:bg-foreground hover:text-background"
                        >
                          [✕ remove]
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                        <Field label="id" value={c.claim_id} onChange={(v) => setClaim(c._uid, { claim_id: v })} />
                        <Field label="about (subject)" value={c.subject} onChange={(v) => setClaim(c._uid, { subject: v })} />
                        <Field label="field name (predicate)" value={c.predicate} onChange={(v) => setClaim(c._uid, { predicate: v })} />
                        <Field label="value" value={String(c.value ?? "")} onChange={(v) => setClaim(c._uid, { value: v })} />
                        <div>
                          <FieldLabel>stored as</FieldLabel>
                          <Select
                            value={c.silo}
                            items={SILOS}
                            onValueChange={(v) => {
                              const silo = v as string;
                              setClaim(c._uid, {
                                silo,
                                render: silo === "crm" ? { as: "field" } : { as: "prose", template: c.render.template ?? "{value}" },
                              });
                            }}
                          >
                            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {SILOS.map((s) => (
                                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <Field label="as of date (ISO, optional)" value={c.asserted_at ?? ""} placeholder="e.g. 2026-02-01T09:00:00Z"
                          onChange={(v) => setClaim(c._uid, { asserted_at: v || null })} />
                        <label><FieldLabel>authority (optional — higher wins ties)</FieldLabel>
                          <Input type="number" value={c.authority ?? ""}
                            onChange={(e) => setClaim(c._uid, { authority: e.target.value === "" ? null : +e.target.value })} /></label>
                        {c.render.as === "prose" && (
                          <Field label={"sentence template — {value} is replaced by the value"} value={c.render.template ?? ""}
                            onChange={(v) => setClaim(c._uid, { render: { as: "prose", template: v } })} />
                        )}
                      </div>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" className="w-full" onClick={addClaim}>
                    + add fact
                  </Button>
                </TabsContent>

                <TabsContent value="probes" className="space-y-2 p-3">
                  {bp.probes.map((p, i) => (
                    <div key={p._uid} className="border border-border p-2">
                      <div className="mb-1.5 flex items-center justify-between">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                          question {i + 1}
                        </span>
                        <button
                          onClick={() => removeProbe(p._uid)}
                          className="text-[10px] text-muted-foreground hover:bg-foreground hover:text-background"
                        >
                          [✕ remove]
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <Field label="id" value={p.probe_id} onChange={(v) => setProbe(p._uid, { probe_id: v })} />
                        <Field label="question" value={p.question} onChange={(v) => setProbe(p._uid, { question: v })} />
                        <div>
                          <FieldLabel>situation (conflict type)</FieldLabel>
                          <Select value={p.conflict_type} items={CONFLICT_TYPES}
                            onValueChange={(v) => setProbe(p._uid, { conflict_type: v as ProbeDef["conflict_type"] })}>
                            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {CONFLICT_TYPES.map((ct) => (
                                <SelectItem key={ct.value} value={ct.value}>{ct.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <FieldLabel>correct behavior</FieldLabel>
                          <Select value={p.expected_behavior}
                            onValueChange={(v) => setProbe(p._uid, { expected_behavior: v as ProbeDef["expected_behavior"] })}>
                            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="answer">answer — commit to the value (answer)</SelectItem>
                              <SelectItem value="refuse">refuse — escalate instead of guessing (refuse)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        {p.expected_behavior === "answer" && (
                          <Field label="expected answer (exact wording)" value={p.expected_answer ?? ""} onChange={(v) => setProbe(p._uid, { expected_answer: v })} />
                        )}
                        {p.conflict_type === "resolvable" && (
                          <div>
                            <FieldLabel>tiebreaker</FieldLabel>
                            <Select value={p.resolution_rule ?? ""} items={RULES}
                              onValueChange={(v) => setProbe(p._uid, { resolution_rule: ((v as string) || null) as ProbeDef["resolution_rule"] })}>
                              <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                              <SelectContent>
                                {RULES.map((r) => (
                                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        )}
                        <Field label="built on facts (ids, comma-sep)" value={(p.references ?? []).join(", ")}
                          onChange={(v) => setProbe(p._uid, { references: csv(v) })} />
                        <Field label="sources it should cite (fact ids, comma-sep)" value={(p.expected_sources ?? []).join(", ")}
                          onChange={(v) => setProbe(p._uid, { expected_sources: csv(v) })} />
                      </div>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" className="w-full" onClick={addProbe}>
                    + add question
                  </Button>
                </TabsContent>
              </Tabs>
            )}
          </Panel>
        </div>

        {/* inspector */}
        <div className="space-y-4 lg:col-span-3">
          <Panel
            title="validation"
            right={
              validation ? (
                validation.ok ? (
                  <span className="border border-border px-1 text-[10px] font-bold uppercase">✓ valid</span>
                ) : (
                  <span className="bg-foreground px-1 text-[10px] font-bold uppercase text-background">
                    ✗ {validation.errors.length}
                  </span>
                )
              ) : undefined
            }
          >
            {!validation ? (
              <div className="text-xs text-muted-foreground">validating…</div>
            ) : validation.ok ? (
              <div className="text-xs">✓ valid — runnable from the run view once saved</div>
            ) : (
              <ValidationErrors errors={validation.errors} />
            )}
          </Panel>

          <Panel title="compiled preview">
            {previewErr && <ErrLine msg={previewErr} />}
            {!preview && !previewErr && (
              <div className="text-xs text-muted-foreground">
                press compile ▸ (editor header) to see the world this dataset produces
              </div>
            )}
            {preview && (
              <div className="space-y-2 text-xs">
                <div className="text-[10px] text-muted-foreground">
                  {Object.keys(preview.manifest).length} facts placed across{" "}
                  {Object.keys(preview.silos).length + preview.docs.length} sources — every
                  fact's location is tracked, so citations can be checked automatically
                </div>
                {Object.entries(preview.silos).map(([silo, subjects]) => (
                  <div key={silo}>
                    <SectionLabel>
                      {silo} records — {Object.keys(subjects).length} accounts
                    </SectionLabel>
                    <div className="max-h-44 overflow-auto border border-border bg-background p-2 text-[11px] leading-relaxed">
                      {Object.entries(subjects).map(([account, fields]) => (
                        <div key={account} className="mb-1">
                          <span className="font-bold">{account}</span>
                          {Object.entries(fields).map(([field, v]) => (
                            <div key={field} className="pl-3">
                              <span className="text-muted-foreground">{field}: </span>
                              {String(v?.value ?? v)}
                              {v?.asserted_at ? (
                                <span className="text-muted-foreground"> · as of {v.asserted_at}</span>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {preview.docs.map((d) => (
                  <div key={d.path}>
                    <SectionLabel>{d.path}</SectionLabel>
                    <pre className="max-h-44 overflow-auto border border-border bg-background p-2 text-[11px] leading-relaxed">
                      {d.content}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      {/* save-as dialog */}
      <Dialog open={saveOpen} onOpenChange={(o) => { setSaveOpen(o); if (!o) setSaveErr(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>save blueprint as…</DialogTitle>
          </DialogHeader>
          <label className="block">
            <FieldLabel>dataset id — letters, digits, - _</FieldLabel>
            <Input
              autoFocus
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && newId) saveAs(); }}
              placeholder="acme-support"
            />
          </label>
          {saveErr && <ErrLine msg={saveErr} />}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveOpen(false)}>cancel</Button>
            <Button disabled={!newId} onClick={saveAs}>create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* discard-unsaved-changes confirm */}
      <AlertDialog open={pending !== null} onOpenChange={(o) => { if (!o) setPending(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>discard unsaved changes?</AlertDialogTitle>
            <AlertDialogDescription>
              the current blueprint has edits that haven't been saved. switching now discards them.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>keep editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (pending?.kind === "load") load(pending.id);
                else if (pending?.kind === "new") doNew();
                setPending(null);
              }}
            >
              discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
