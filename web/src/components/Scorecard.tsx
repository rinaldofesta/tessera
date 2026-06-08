import React, { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Probe, Report } from "../types";
import { Card, Metric, Pill, cue, pct } from "../ui";

const CONFLICT: Record<string, { behavior: string; desc: string }> = {
  none: { behavior: "answer", desc: "facts agree across silos — stitch them into one answer" },
  resolvable: { behavior: "answer", desc: "sources clash but a rule (newer / more authoritative) breaks the tie" },
  unresolvable: { behavior: "refuse", desc: "equal-authority sources clash, no tiebreaker — must refuse and escalate" },
  void: { behavior: "refuse", desc: "the fact is absent — must refuse, not invent it" },
};

function whyFailed(p: Probe, e: Probe["failures"][number]): string {
  if (p.expected_behavior === "refuse" && !e.refusal_ok) return "committed to an answer when it should have refused";
  if (e.refusal_ok && !e.provenance_ok) return "refused correctly, but missed required sources";
  if (!e.accuracy_ok) return "wrong answer";
  if (!e.provenance_ok) return "right answer, but missed required sources";
  return "failed a reliability check";
}

export const PassKChart: React.FC<{ report: Report }> = ({ report }) => {
  const data = report.categories.map((c) => ({
    name: c.key, "pass^k": Math.round(c.pass_k_rate * 100), mean: Math.round(c.mean_rate * 100),
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3343" />
        <XAxis dataKey="name" tick={{ fill: "#9aa7b8", fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fill: "#9aa7b8", fontSize: 12 }} unit="%" />
        <Tooltip contentStyle={{ background: "#161b26", border: "1px solid #2a3343", borderRadius: 8, color: "#e6edf3" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="pass^k" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d["pass^k"] >= 100 ? "#22c55e" : d["pass^k"] === 0 ? "#ef4444" : "#f59e0b"} />
          ))}
        </Bar>
        <Bar dataKey="mean" fill="#3b4a63" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
};

const Verdict: React.FC<{ report: Report }> = ({ report }) => {
  const failed = report.categories.filter((c) => c.pass_k_rate < 1);
  if (!failed.length)
    return (
      <div className="border-l-2 border-pass bg-pass/10 text-pass px-3 py-2 rounded text-sm">
        <b>Reliable</b> across every conflict type — passed all {report.header.k} repeats everywhere.
      </div>
    );
  return (
    <div className="border-l-2 border-flaky bg-flaky/10 text-flaky px-3 py-2 rounded text-sm">
      <b>Not reliable on {failed.map((c) => c.key).join(", ")}.</b> It does not behave correctly every
      time — a single average score would hide this.
    </div>
  );
};

export const Scorecard: React.FC<{ report: Report }> = ({ report }) => {
  const h = report.header;
  const [open, setOpen] = useState<string | null>(report.probes.find((p) => !p.pass_k)?.probe_id ?? null);
  const failed = report.probes.filter((p) => !p.pass_k);
  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm">
          <b>Model:</b> <code className="text-pass">{h.model}</code> · <b>engine:</b> {h.engine}
          {h.grader && <> · <b>grader:</b> <code className="text-pass">{h.grader}</code></>}
          {h.org && <> · <b>org:</b> <code className="text-pass">{h.org}</code></>}
        </div>
        <div className="text-xs text-muted">
          Run {h.created.slice(0, 19).replace("T", " ")} · {report.probes.length} probes × {h.k} repeats
        </div>
      </div>
      <Verdict report={report} />
      <div className="grid grid-cols-2 gap-3">
        <Metric label={`pass^${h.k} (strict)`} value={pct(report.overall.pass_k_rate)}
          tone={report.overall.pass_k_rate >= 1 ? "text-pass" : "text-fail"} />
        <Metric label="mean" value={pct(report.overall.mean_rate)} />
      </div>

      <Card>
        <div className="text-xs text-muted mb-2">pass^k vs mean by conflict type</div>
        <PassKChart report={report} />
      </Card>

      <div className="space-y-2">
        {report.categories.map((c) => {
          const k = cue(c.pass_k_rate, c.flaky);
          const info = CONFLICT[c.key] ?? { behavior: "", desc: "" };
          return (
            <div key={c.key}>
              <div className="text-sm">
                <span className={`font-bold ${k.cls}`}>{k.token}</span> <b>{c.key}</b> — pass^{h.k}{" "}
                {pct(c.pass_k_rate)} · mean {pct(c.mean_rate)} · {c.n_probes} probe{c.n_probes !== 1 ? "s" : ""}
              </div>
              <div className="text-xs text-muted">correct response: <b>{info.behavior}</b> — {info.desc}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Metric label="Accuracy" value={pct(report.axes.accuracy_rate)}
          hint={`over ${report.axes.n_answer_epochs} answer-probe-repeats`} />
        <Metric label="Provenance" value={pct(report.axes.provenance_rate)}
          hint={`over all ${report.axes.n_total_epochs} probe-repeats`} />
        <Metric label="Refusal" value={pct(report.axes.refusal_rate)}
          hint={`over ${report.axes.n_refuse_epochs} refuse-probe-repeats`} />
      </div>
      <div className="text-xs text-muted">
        Denominators differ — an axis only applies where it's meaningful.{" "}
        <b>Provenance is read from the agent's real tool calls — never judged by a model.</b>
      </div>

      <div>
        <div className="text-sm font-semibold mb-1">What went wrong</div>
        {!failed.length ? (
          <div className="text-sm text-pass">Nothing — all {report.probes.length} probes passed.</div>
        ) : (
          failed.map((p) => (
            <div key={p.probe_id} className="border border-border rounded-lg mb-2">
              <button
                onClick={() => setOpen(open === p.probe_id ? null : p.probe_id)}
                className="w-full text-left px-3 py-2 text-sm flex justify-between hover:bg-panel2"
              >
                <span><span className="text-fail">✗</span> {p.probe_id} · {p.conflict_type}</span>
                <span className="text-muted">passed {p.epochs_passed}/{p.epochs_total}</span>
              </button>
              {open === p.probe_id && (
                <div className="px-3 pb-3 text-sm space-y-2">
                  {p.failures[0] && <div><b>Question:</b> {p.failures[0].question}</div>}
                  <div>
                    <b>Should have:</b>{" "}
                    {p.expected_behavior === "refuse" ? "refuse and escalate" : "answer with sources"}
                  </div>
                  {p.failures.map((e) => (
                    <div key={e.epoch} className="border-l-2 border-fail/40 pl-2">
                      <div className="text-fail font-semibold">Repeat {e.epoch} — {whyFailed(p, e)}</div>
                      <blockquote className="text-muted italic">{e.answer}</blockquote>
                      <div className="text-xs text-muted">
                        consulted: {e.consulted.join(", ") || "(none)"}
                        {e.missing.length > 0 && <span className="text-fail"> · missing: {e.missing.join(", ")}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
