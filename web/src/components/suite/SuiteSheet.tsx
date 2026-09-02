import { useEffect, useRef, useState } from "react";
import { LockKeyhole } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/api";
import { ScenarioCards } from "@/components/ScenarioCards";
import { ValidationErrors } from "@/components/form";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { SUITE_COPY } from "@/copy";
import { useCatalog } from "@/hooks";
import { messageOf } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Artifacts, Blueprint, Claim, ProbeDef, ValidationResult } from "@/types";

const EMPTY_BLUEPRINT: Blueprint = { claims: [], probes: [] };
const VALID_NAME = /^[A-Za-z0-9][A-Za-z0-9_-]*$/;
const ALIASES = new Set(["toy"]);
// "new" is the ?edit=new sentinel for the create-suite flow — a suite actually named
// "new" would be indistinguishable from it and permanently unreachable afterward.
const SENTINELS = new Set(["new"]);

function suitePath(name: string) {
  return `~/.tessera/suites/${name || "<name>"}.json`;
}

/** The one place that knows how the "edit" query param opens/closes this sheet —
    shared with Run.tsx's own "manage suites" link so both stay in lockstep. */
export function withSuiteEdit(params: URLSearchParams, next: string | null): URLSearchParams {
  const updated = new URLSearchParams(params);
  if (next === null) updated.delete("edit");
  else updated.set("edit", next);
  return updated;
}

export function SuiteSheet({ onSaved, onDeleted = () => {} }: {
  onSaved: (name: string) => void;
  /** Fires after a suite is deleted, so a caller holding that name selected elsewhere
      (e.g. the run form) can fall back instead of pointing at a suite that's now gone. */
  onDeleted?: (name: string) => void;
}) {
  const { catalog, reload } = useCatalog();
  const [params, setParams] = useSearchParams();
  // ?edit=new | ?edit=<name> — its own parameter, so a rerun prefill's ?suite= never opens the sheet
  const selected = params.get("edit");
  const open = selected !== null;
  const isNew = selected === "new";
  const suite = catalog?.suites.find((item) => item.name === selected);
  const builtin = suite?.kind === "builtin";
  const [name, setName] = useState("");
  const [blueprint, setBlueprint] = useState<Blueprint>(EMPTY_BLUEPRINT);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [preview, setPreview] = useState<Artifacts | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [pendingNav, setPendingNav] = useState<{ next: string | null } | null>(null);
  const duplicateSeed = useRef<Blueprint | null>(null);
  const loadGeneration = useRef(0);

  // raw param mutation — bypasses the unsaved-changes guard below, for callers that
  // already know there's nothing to lose (a fresh save/delete, or copying a read-only builtin)
  function applyChoose(next: string) {
    setParams((current) => withSuiteEdit(current, next));
  }

  function applyClose() {
    setParams((current) => withSuiteEdit(current, null));
  }

  // guarded entry points: if there are unsaved edits, ask before discarding them —
  // switching suites or closing the sheet used to be a silent data loss otherwise
  function choose(next: string) {
    if (dirty && next !== selected) setPendingNav({ next });
    else applyChoose(next);
  }

  function close() {
    if (dirty) setPendingNav({ next: null });
    else applyClose();
  }

  function confirmDiscard() {
    if (!pendingNav) return;
    if (pendingNav.next === null) applyClose();
    else applyChoose(pendingNav.next);
    setPendingNav(null);
  }

  useEffect(() => {
    if (!open) return;
    const generation = ++loadGeneration.current;
    setError(null);
    setValidation(null);
    setPreview(null);
    setDirty(false);
    if (isNew) {
      setName("");
      setBlueprint(duplicateSeed.current ?? EMPTY_BLUEPRINT);
      duplicateSeed.current = null;
      setLoading(false);
      return;
    }
    if (!selected) return;
    setName(selected);
    setLoading(true);
    api.getBlueprint(selected)
      .then((next) => {
        if (loadGeneration.current === generation) setBlueprint({ claims: next.claims, probes: next.probes ?? [] });
      })
      .catch((caught) => {
        // clear the previous suite's content too — otherwise it lingers under the new
        // suite's name/error, and a stray Save would overwrite it with the wrong data.
        if (loadGeneration.current === generation) {
          setError(messageOf(caught));
          setBlueprint(EMPTY_BLUEPRINT);
        }
      })
      .finally(() => {
        if (loadGeneration.current === generation) setLoading(false);
      });
  }, [isNew, open, selected]);

  useEffect(() => {
    if (!open || loading) return;
    let alive = true;
    const timer = setTimeout(() => {
      api.validateBlueprint(blueprint)
        .then((result) => { if (alive) setValidation(result); })
        .catch((caught) => {
          if (alive) setValidation({ ok: false, errors: [{ location: "(api)", message: messageOf(caught) }] });
        });
      if ((blueprint.probes ?? []).length > 0) {
        api.previewBlueprint(blueprint)
          .then((result) => { if (alive) setPreview(result); })
          .catch(() => { if (alive) setPreview(null); });
      }
    }, 350);
    return () => { alive = false; clearTimeout(timer); };
  }, [blueprint, loading, open]);

  const reserved = new Set([
    ...ALIASES,
    ...SENTINELS,
    ...(catalog?.suites.filter((item) => item.kind === "builtin").map((item) => item.name) ?? []),
  ]);
  const existingUser = catalog?.suites.some((item) => item.kind === "user" && item.name === name);
  const nameError = !name
    ? SUITE_COPY.nameRequired
    : !VALID_NAME.test(name)
      ? SUITE_COPY.nameInvalid
      : reserved.has(name)
        ? SUITE_COPY.nameReserved
        : isNew && existingUser
          ? SUITE_COPY.nameExists
          : null;
  const savedName = isNew ? name : selected ?? name;
  const silos = preview
    ? Array.from(new Set(blueprint.claims.map((claim) => claim.silo))).sort()
    : [];

  function insertScenario(claims: Claim[], probe: ProbeDef) {
    setDirty(true);
    setBlueprint((current) => ({
      claims: [...current.claims, ...claims],
      probes: [...(current.probes ?? []), probe],
    }));
  }

  // undoes one insertScenario: drops the probe and every claim only it referenced,
  // leaving claims other probes still reference untouched
  function removeScenario(probeId: string) {
    setDirty(true);
    setBlueprint((current) => {
      const target = (current.probes ?? []).find((p) => p.probe_id === probeId);
      const remainingProbes = (current.probes ?? []).filter((p) => p.probe_id !== probeId);
      const stillReferenced = new Set(remainingProbes.flatMap((p) => p.references ?? []));
      const orphaned = new Set((target?.references ?? []).filter((id) => !stillReferenced.has(id)));
      return {
        claims: current.claims.filter((c) => !orphaned.has(c.claim_id)),
        probes: remainingProbes,
      };
    });
  }

  async function save() {
    // `loading` guards against saving stale content still in flight from a suite
    // switch — the button is disabled for the same reason, this is the backstop.
    if (nameError || !savedName || loading) return;
    setSaving(true);
    setError(null);
    try {
      if (isNew) await api.createBlueprint(savedName, blueprint);
      else await api.saveBlueprint(savedName, blueprint);
      reload();
      onSaved(savedName);
      setDirty(false);
      applyClose(); // already persisted — nothing left to confirm discarding
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!selected) return;
    setError(null);
    try {
      await api.deleteBlueprint(selected);
      reload();
      onDeleted(selected);
      setDirty(false);
      applyClose(); // the whole suite is gone — nothing left to confirm discarding
    } catch (caught) {
      setError(messageOf(caught));
    }
  }

  function duplicate() {
    duplicateSeed.current = blueprint;
    applyChoose("new"); // source is a read-only builtin, so it's never dirty
  }

  return (
    <>
    <Dialog open={open} onOpenChange={(next) => { if (!next) close(); }}>
      <DialogContent className="top-0 right-0 left-auto h-dvh max-w-5xl translate-x-0 translate-y-0 overflow-hidden rounded-none p-0 sm:max-w-5xl">
        <DialogHeader className="sr-only">
          <DialogTitle>{SUITE_COPY.title}</DialogTitle>
          <DialogDescription>{SUITE_COPY.description}</DialogDescription>
        </DialogHeader>
        <div className="grid min-h-0 grid-cols-1 md:grid-cols-[14rem_minmax(0,1fr)]">
          <aside className="border-b border-line bg-sunken p-4 md:border-r md:border-b-0">
            <p className="mb-3 font-display text-lg font-semibold">{SUITE_COPY.title}</p>
            <nav aria-label={SUITE_COPY.listLabel} className="grid gap-1">
              <button
                className={cn(
                  "rounded-lg px-3 py-2 text-left text-sm hover:bg-raised",
                  isNew && "bg-primary/10 font-medium text-primary",
                )}
                onClick={() => choose("new")}
              >
                {SUITE_COPY.newSuite}
              </button>
              {catalog?.suites.map((item) => (
                <button
                  key={item.name}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-raised",
                    selected === item.name && "bg-primary/10 font-medium text-primary",
                  )}
                  onClick={() => choose(item.name)}
                >
                  {item.kind === "builtin" && <LockKeyhole aria-label={SUITE_COPY.readOnly} className="size-3.5" />}
                  <span className="truncate">{item.label}</span>
                </button>
              ))}
            </nav>
          </aside>

          <main className="flex min-h-0 flex-col bg-panel">
            <div className="flex-1 overflow-y-auto p-5 pr-12 md:p-7 md:pr-14">
              <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                <label className="min-w-56 flex-1">
                  <span className="mb-1 block text-xs font-medium text-muted-foreground">{SUITE_COPY.nameLabel}</span>
                  <Input
                    aria-label={SUITE_COPY.nameLabel}
                    autoFocus={isNew}
                    disabled={!isNew}
                    value={name}
                    placeholder={SUITE_COPY.namePlaceholder}
                    onChange={(event) => { setName(event.target.value); setDirty(true); }}
                  />
                </label>
                {builtin ? (
                  <Button onClick={duplicate}>{SUITE_COPY.duplicate}</Button>
                ) : (
                  <div className="flex gap-2">
                    {!isNew && selected && (
                      <AlertDialog>
                        <AlertDialogTrigger render={<Button variant="outline" />}>
                          {SUITE_COPY.delete}
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>{SUITE_COPY.deleteTitle(selected)}</AlertDialogTitle>
                            <AlertDialogDescription>{SUITE_COPY.deleteDescription}</AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>{SUITE_COPY.cancel}</AlertDialogCancel>
                            <AlertDialogAction onClick={remove}>{SUITE_COPY.confirmDelete}</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                    <Button disabled={loading || saving || !!nameError || validation?.ok === false || (blueprint.probes ?? []).length === 0} onClick={save}>
                      {saving ? SUITE_COPY.saving : SUITE_COPY.save}
                    </Button>
                  </div>
                )}
              </div>

              {isNew && nameError && <p role="alert" className="mb-4 text-xs text-verdict-unreliable">{nameError}</p>}
              {error && <p role="alert" className="mb-4 text-sm text-verdict-unreliable">{error}</p>}

              {loading ? (
                <p className="text-sm text-faint">{SUITE_COPY.loading}</p>
              ) : (
                <>
                  <div className="mb-4 rounded-lg border border-line bg-raised px-3 py-2 text-xs text-muted-foreground">
                    {SUITE_COPY.preview((blueprint.probes ?? []).length, blueprint.claims.length, silos)}
                  </div>
                  <ScenarioCards
                    claims={blueprint.claims}
                    probes={blueprint.probes ?? []}
                    onInsert={insertScenario}
                    onRemove={removeScenario}
                    readOnly={builtin}
                  />
                  {!builtin && validation && !validation.ok && (
                    <div className="mt-4 rounded-lg border border-line p-3">
                      <ValidationErrors errors={validation.errors} />
                    </div>
                  )}
                </>
              )}
            </div>

            <footer className="border-t border-line bg-sunken px-5 py-3 font-mono text-xs text-muted-foreground md:px-7">
              {suitePath(savedName)} — {SUITE_COPY.editAnywhere}
            </footer>
          </main>
        </div>
      </DialogContent>
    </Dialog>

    <AlertDialog open={pendingNav !== null} onOpenChange={(next) => { if (!next) setPendingNav(null); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{SUITE_COPY.discardTitle}</AlertDialogTitle>
          <AlertDialogDescription>{SUITE_COPY.discardDescription}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{SUITE_COPY.cancel}</AlertDialogCancel>
          <AlertDialogAction onClick={confirmDiscard}>{SUITE_COPY.discardConfirm}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    </>
  );
}
