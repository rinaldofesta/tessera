import React from "react";

export const pct = (x: number | null | undefined) =>
  x === null || x === undefined ? "n/a" : `${Math.round(x * 100)}%`;

export function cue(passK: number, flaky: boolean) {
  if (passK >= 1) return { token: "PASS", cls: "text-pass", dot: "bg-pass" };
  if (flaky) return { token: "FLAKY", cls: "text-flaky", dot: "bg-flaky" };
  return { token: "FAIL", cls: "text-fail", dot: "bg-fail" };
}

export const Card: React.FC<React.PropsWithChildren<{ className?: string }>> = ({ children, className = "" }) => (
  <div className={`bg-panel border border-border rounded-xl p-4 ${className}`}>{children}</div>
);

export const Btn: React.FC<
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }
> = ({ variant = "primary", className = "", ...p }) => {
  const styles = {
    primary: "bg-accent text-[#06210f] hover:brightness-110",
    ghost: "bg-transparent border border-border text-ink hover:bg-panel2",
    danger: "bg-transparent border border-fail/50 text-fail hover:bg-fail/10",
  }[variant];
  return (
    <button
      {...p}
      className={`px-3.5 py-2 rounded-lg text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition ${styles} ${className}`}
    />
  );
};

export const Pill: React.FC<React.PropsWithChildren<{ tone?: "pass" | "fail" | "flaky" | "muted" }>> = ({
  children, tone = "muted",
}) => {
  const tones = {
    pass: "text-pass border-pass/40 bg-pass/10",
    fail: "text-fail border-fail/40 bg-fail/10",
    flaky: "text-flaky border-flaky/40 bg-flaky/10",
    muted: "text-muted border-border bg-panel2",
  }[tone];
  return <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold border ${tones}`}>{children}</span>;
};

export const Metric: React.FC<{ label: string; value: string; hint?: string; tone?: string }> = ({
  label, value, hint, tone = "text-ink",
}) => (
  <div className="bg-panel2 border border-border rounded-xl px-4 py-3" title={hint}>
    <div className="text-xs text-muted">{label}</div>
    <div className={`text-2xl font-extrabold ${tone}`}>{value}</div>
  </div>
);

export const Spinner = () => (
  <span className="inline-block w-4 h-4 border-2 border-muted border-t-accent rounded-full animate-spin align-middle" />
);

export const Field: React.FC<React.PropsWithChildren<{ label: string }>> = ({ label, children }) => (
  <label className="block mb-3">
    <span className="block text-xs text-muted mb-1">{label}</span>
    {children}
  </label>
);

export const inputCls =
  "w-full bg-panel2 border border-border rounded-lg px-3 py-2 text-sm text-ink focus:border-accent outline-none";

export const ErrorBox: React.FC<{ msg: string }> = ({ msg }) => (
  <div className="border-l-2 border-fail bg-fail/10 text-fail px-3 py-2 rounded text-sm whitespace-pre-wrap">{msg}</div>
);

export const SectionTitle: React.FC<React.PropsWithChildren> = ({ children }) => (
  <h3 className="text-sm font-bold text-muted uppercase tracking-wide mt-6 mb-2">{children}</h3>
);
