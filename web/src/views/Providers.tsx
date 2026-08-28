import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { api } from "@/api";
import { PROVIDER_COPY, PROVIDER_LABELS } from "@/copy";
import { useAsync } from "@/hooks";
import type { Provider, ProviderField, ProviderUpdate } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

function fieldValue(
  field: ProviderField,
  values: Record<string, string>,
): string {
  return values[field.id] ?? "";
}

function ProviderRow({
  provider,
  onSaved,
}: {
  provider: Provider;
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const editorId = `provider-${PROVIDER_LABELS[provider.id] ?? provider.id}-fields`;
  const hasValue = provider.fields.some((field) => fieldValue(field, values).trim());

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body: ProviderUpdate = {};

    for (const field of provider.fields) {
      const value = fieldValue(field, values).trim();
      if (field.id === "api_key" && value) body.api_key = value;
      if (field.id === "base_url" && value) body.base_url = value;
    }

    if (!body.api_key && !body.base_url) return;

    setSaving(true);
    try {
      await api.saveProvider(provider.id, body);
      toast.success(PROVIDER_COPY.saved(provider.id), {
        description: PROVIDER_COPY.savedHint,
      });
      setOpen(false);
      setValues({});
      onSaved();
    } catch (error) {
      toast.error(PROVIDER_COPY.saveFailed, {
        description: error instanceof Error ? error.message : String(error),
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-[var(--card)] px-3.5 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="min-w-32 flex-1 text-[14px]">{PROVIDER_LABELS[provider.id] ?? provider.id}</span>
        <span className="font-mono text-[10.5px] text-[var(--faint)]">
          {provider.fields.map((field) => field.env_var).join(" · ")}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-expanded={open}
          aria-controls={editorId}
          onClick={() => setOpen((current) => !current)}
        >
          {provider.configured ? PROVIDER_COPY.replace : PROVIDER_COPY.add}
        </Button>
        <Badge
          variant="outline"
          className={
            provider.configured
              ? "border-[var(--verdict-reliable)]/55 text-[var(--verdict-reliable)]"
              : "border-[var(--border)] text-[var(--faint)]"
          }
        >
          {provider.configured ? PROVIDER_COPY.configured : PROVIDER_COPY.notConfigured}
        </Badge>
      </div>

      {open && (
        <form id={editorId} onSubmit={save} className="mt-3 grid max-w-xl gap-3">
          {provider.fields.map((field) => {
            const inputId = `${PROVIDER_LABELS[provider.id] ?? provider.id}-${field.id}`;
            const isApiKey = field.id === "api_key";

            return (
              <div key={field.id} className="grid gap-1.5">
                <Label
                  htmlFor={inputId}
                  className="font-mono text-[10.5px] text-[var(--faint)]"
                >
                  {field.env_var}
                </Label>
                <Input
                  id={inputId}
                  type={isApiKey ? "password" : "url"}
                  autoComplete="off"
                  placeholder={
                    isApiKey ? PROVIDER_COPY.keyPlaceholder : PROVIDER_COPY.urlPlaceholder
                  }
                  value={fieldValue(field, values)}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      [field.id]: event.target.value,
                    }))
                  }
                  className="font-mono text-[12px]"
                />
              </div>
            );
          })}
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" size="sm" disabled={saving || !hasValue}>
              {saving ? PROVIDER_COPY.saving : PROVIDER_COPY.save}
            </Button>
            <span className="text-[11px] text-[var(--faint)]">
              {PROVIDER_COPY.savedHint}
            </span>
          </div>
        </form>
      )}
    </div>
  );
}

export default function Providers() {
  const providers = useAsync(() => api.listProviders(), []);
  const list = providers.data ?? [];
  const configured = list.filter((provider) => provider.configured);
  const notConfigured = list.filter((provider) => !provider.configured);
  const groups = [
    { label: PROVIDER_COPY.configuredGroup, items: configured },
    { label: PROVIDER_COPY.notConfiguredGroup, items: notConfigured },
  ].filter((group) => group.items.length > 0);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="font-display text-2xl font-bold tracking-tight">
        {PROVIDER_COPY.title}
      </h1>
      <p className="mt-1 mb-5 text-sm text-[var(--muted-foreground)]">
        {PROVIDER_COPY.subtitle}
      </p>

      {providers.loading ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <Card className="gap-0 py-0">
          {groups.map((group, groupIndex) => (
            <div key={group.label}>
              {groupIndex > 0 && <Separator />}
              <p className="bg-[#101216] px-3.5 pt-2.5 pb-1.5 font-mono text-[10.5px] uppercase tracking-[0.12em] text-[var(--faint)]">
                {group.label}
              </p>
              <Separator />
              {group.items.map((provider, providerIndex) => (
                <div key={PROVIDER_LABELS[provider.id] ?? provider.id}>
                  {providerIndex > 0 && <Separator />}
                  <ProviderRow provider={provider} onSaved={providers.reload} />
                </div>
              ))}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
