import { useEffect, useState } from "react";
import { api } from "../api";
import { useAsync } from "../hooks";
import type { Artifacts, Blueprint, Claim, ProbeDef, ValidationResult } from "../types";
import { Btn, Card, ErrorBox, Pill, Spinner, inputCls } from "../ui";

const EMPTY: Blueprint = { claims: [], probes: [] };
const newClaim = (): Claim => ({ claim_id: "", subject: "", predicate: "", value: "", silo: "crm", render: { as: "field" } });
const newProbe = (): ProbeDef => ({ probe_id: "", question: "", references: [], conflict_type: "none", expected_behavior: "answer", expected_answer: "", expected_sources: [] });
const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function Datasets() {
  const list = useAsync(() => api.listBlueprints(), []);
  const [selected, setSelected] = useState<string>("");
  const [bp, setBp] = useState<Blueprint>(EMPTY);
  const [loadingBp, setLoadingBp] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [preview, setPreview] = useState<Artifacts | null>(null);
  const [msg, setMsg] = useState<string>("");

  const ids = list.data ?? [];
  useEffect(() => { if (!selected && ids.length) load(ids[0].id); }, [list.data]); // eslint-disable-line

  function load(id: string) {
    setSelected(id); setLoadingBp(true); setMsg("");
    api.getBlueprint(id).then((b) => setBp(b)).finally(() => setLoadingBp(false));
  }
  function startNew() { setSelected(""); setBp({ claims: [newClaim()], probes: [newProbe()] }); setMsg("new — edit then Save as…"); }

  // live validation (debounced)
  useEffect(() => {
    const t = setTimeout(() => api.validateBlueprint(bp).then(setValidation).catch(() => setValidation(null)), 400);
    return () => clearTimeout(t);
  }, [bp]);

  const update = (patch: Partial<Blueprint>) => setBp((b) => ({ ...b, ...patch }));
  const setClaim = (i: number, c: Partial<Claim>) => update({ claims: bp.claims.map((x, j) => (j === i ? { ...x, ...c } : x)) });
  const setProbe = (i: number, p: Partial<ProbeDef>) => update({ probes: bp.probes.map((x, j) => (j === i ? { ...x, ...p } : x)) });

  async function doPreview() {
    setMsg(""); try { setPreview(await api.previewBlueprint(bp)); } catch (e: any) { setMsg(`preview failed: ${e.message}`); }
  }
  async function save() {
    try {
      if (selected) { await api.saveBlueprint(selected, bp); setMsg(`saved '${selected}'`); }
      else { const id = prompt("New dataset id (letters, digits, - _):"); if (!id) return; await api.createBlueprint(id, bp); setMsg(`created '${id}'`); setSelected(id); }
      list.reload();
    } catch (e: any) { setMsg(`save failed: ${e.message}`); }
  }
  async function remove() {
    if (!selected || !confirm(`Delete '${selected}'?`)) return;
    await api.deleteBlueprint(selected); setSelected(""); setBp(EMPTY); list.reload();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Datasets</h1>
      <p className="text-sm text-muted mb-4">Author the blueprint — Claims (facts) + Probes (questions) — that defines an eval. Validated and compiled live; nothing leaves your machine.</p>

      <div className="flex gap-2 items-center mb-4 flex-wrap">
        <select className={`${inputCls} max-w-xs`} value={selected} onChange={(e) => load(e.target.value)}>
          <option value="" disabled>— pick a dataset —</option>
          {ids.map((b) => <option key={b.id} value={b.id}>{b.id} ({b.claims}c / {b.probes}p)</option>)}
        </select>
        <Btn variant="ghost" onClick={startNew}>+ New</Btn>
        <Btn onClick={save}>{selected ? "Save" : "Save as…"}</Btn>
        <Btn variant="ghost" onClick={doPreview}>Preview compiled org</Btn>
        {selected && <Btn variant="danger" onClick={remove}>Delete</Btn>}
        {msg && <span className="text-xs text-muted">{msg}</span>}
        {validation && (
          <span className="ml-auto">
            {validation.ok ? <Pill tone="pass">valid</Pill> : <Pill tone="fail">{validation.errors.length} error(s)</Pill>}
          </span>
        )}
      </div>

      {loadingBp && <Spinner />}

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 space-y-4">
          {/* Claims */}
          <Card>
            <div className="flex justify-between mb-2"><b className="text-sm">Claims (facts)</b>
              <Btn variant="ghost" onClick={() => update({ claims: [...bp.claims, newClaim()] })}>+ claim</Btn></div>
            {bp.claims.map((c, i) => (
              <div key={i} className="border border-border rounded-lg p-2 mb-2 grid grid-cols-2 gap-2">
                <input className={inputCls} placeholder="claim_id" value={c.claim_id} onChange={(e) => setClaim(i, { claim_id: e.target.value })} />
                <input className={inputCls} placeholder="subject" value={c.subject} onChange={(e) => setClaim(i, { subject: e.target.value })} />
                <input className={inputCls} placeholder="predicate" value={c.predicate} onChange={(e) => setClaim(i, { predicate: e.target.value })} />
                <input className={inputCls} placeholder="value" value={String(c.value ?? "")} onChange={(e) => setClaim(i, { value: e.target.value })} />
                <select className={inputCls} value={c.silo}
                  onChange={(e) => { const silo = e.target.value; setClaim(i, { silo, render: silo === "crm" ? { as: "field" } : { as: "prose", template: c.render.template ?? "{value}" } }); }}>
                  <option value="crm">crm (field)</option><option value="docs">docs (prose)</option>
                </select>
                <input className={inputCls} placeholder="asserted_at (ISO, optional)" value={c.asserted_at ?? ""} onChange={(e) => setClaim(i, { asserted_at: e.target.value || null })} />
                {c.render.as === "prose" && (
                  <input className={`${inputCls} col-span-2`} placeholder="prose template, use {value}" value={c.render.template ?? ""}
                    onChange={(e) => setClaim(i, { render: { as: "prose", template: e.target.value } })} />
                )}
                <input className={inputCls} type="number" placeholder="authority (optional)" value={c.authority ?? ""} onChange={(e) => setClaim(i, { authority: e.target.value === "" ? null : +e.target.value })} />
                <div className="flex justify-end"><Btn variant="danger" onClick={() => update({ claims: bp.claims.filter((_, j) => j !== i) })}>remove</Btn></div>
              </div>
            ))}
          </Card>

          {/* Probes */}
          <Card>
            <div className="flex justify-between mb-2"><b className="text-sm">Probes (questions)</b>
              <Btn variant="ghost" onClick={() => update({ probes: [...bp.probes, newProbe()] })}>+ probe</Btn></div>
            {bp.probes.map((p, i) => (
              <div key={i} className="border border-border rounded-lg p-2 mb-2 grid grid-cols-2 gap-2">
                <input className={inputCls} placeholder="probe_id" value={p.probe_id} onChange={(e) => setProbe(i, { probe_id: e.target.value })} />
                <input className={inputCls} placeholder="question" value={p.question} onChange={(e) => setProbe(i, { question: e.target.value })} />
                <select className={inputCls} value={p.conflict_type} onChange={(e) => setProbe(i, { conflict_type: e.target.value as ProbeDef["conflict_type"] })}>
                  <option value="none">none</option><option value="resolvable">resolvable</option>
                  <option value="unresolvable">unresolvable</option><option value="void">void</option>
                </select>
                <select className={inputCls} value={p.expected_behavior} onChange={(e) => setProbe(i, { expected_behavior: e.target.value as ProbeDef["expected_behavior"] })}>
                  <option value="answer">answer</option><option value="refuse">refuse</option>
                </select>
                {p.expected_behavior === "answer" && (
                  <input className={inputCls} placeholder="expected_answer" value={p.expected_answer ?? ""} onChange={(e) => setProbe(i, { expected_answer: e.target.value })} />
                )}
                {p.conflict_type === "resolvable" && (
                  <select className={inputCls} value={p.resolution_rule ?? ""} onChange={(e) => setProbe(i, { resolution_rule: (e.target.value || null) as ProbeDef["resolution_rule"] })}>
                    <option value="">— rule —</option><option value="recency_wins">recency_wins</option><option value="authority_wins">authority_wins</option>
                  </select>
                )}
                <input className={inputCls} placeholder="references (claim_ids, comma-sep)" value={p.references.join(", ")} onChange={(e) => setProbe(i, { references: csv(e.target.value) })} />
                <input className={inputCls} placeholder="expected_sources (claim_ids, comma-sep)" value={p.expected_sources.join(", ")} onChange={(e) => setProbe(i, { expected_sources: csv(e.target.value) })} />
                <div className="col-span-2 flex justify-end"><Btn variant="danger" onClick={() => update({ probes: bp.probes.filter((_, j) => j !== i) })}>remove</Btn></div>
              </div>
            ))}
          </Card>
        </div>

        {/* Inspector */}
        <div className="space-y-4">
          <Card>
            <b className="text-sm">Validation</b>
            {!validation ? <div className="text-xs text-muted mt-1">…</div> : validation.ok ? (
              <div className="text-sm text-pass mt-1">✓ valid — ready to run</div>
            ) : (
              <ul className="text-xs text-fail mt-2 space-y-1">
                {validation.errors.map((e, i) => <li key={i}><code>{e.location}</code>: {e.message}</li>)}
              </ul>
            )}
          </Card>
          <Card>
            <b className="text-sm">Compiled preview</b>
            {!preview ? <div className="text-xs text-muted mt-1">Click “Preview compiled org”.</div> : (
              <div className="mt-2 text-xs space-y-2">
                {Object.entries(preview.silos).map(([silo, subjects]) => (
                  <div key={silo}>
                    <div className="text-muted">crm silo: <code>{silo}/db.json</code></div>
                    <pre className="bg-[#0b0f17] border border-border rounded p-2 overflow-auto">{JSON.stringify(subjects, null, 2)}</pre>
                  </div>
                ))}
                {preview.docs.map((d) => (
                  <div key={d.path}>
                    <div className="text-muted"><code>{d.path}</code></div>
                    <pre className="bg-[#0b0f17] border border-border rounded p-2 overflow-auto">{d.content}</pre>
                  </div>
                ))}
                <div className="text-muted">{Object.keys(preview.manifest).length} claims in manifest</div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
