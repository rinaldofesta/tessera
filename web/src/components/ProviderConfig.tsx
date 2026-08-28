import { useState, type FormEvent } from "react";
import { api } from "@/api";
import type { components } from "@/api-types.gen";
import { LAUNCHER_COPY } from "@/copy";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type ApiSchema = components["schemas"];
type Provider = ApiSchema["Provider"];
type ProviderUpdate = ApiSchema["ProviderUpdate"];

export function ProviderConfig({
  provider,
  onSaved,
}: {
  provider: Provider;
  onSaved: (providerId: string) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasValue = Object.values(values).some((value) => value.trim().length > 0);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body: ProviderUpdate = {};
    if (values.api_key?.trim()) body.api_key = values.api_key.trim();
    if (values.base_url?.trim()) body.base_url = values.base_url.trim();

    setSaving(true);
    setError(null);
    try {
      const updated = await api.saveProvider(provider.id, body);
      setValues({});
      onSaved(updated.id);
    } catch (caught) {
      const detail = caught instanceof Error ? caught.message : String(caught);
      setError(LAUNCHER_COPY.providerSaveFailed(detail));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-2 border border-border bg-background p-3">
      <div className="font-heading text-sm font-semibold">{provider.id}</div>
      {provider.fields.map((field) => {
        const inputId = `provider-${provider.id}-${field.id}`;
        return (
          <div key={field.id} className="space-y-1">
            <Label
              htmlFor={inputId}
              className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground"
            >
              {field.env_var}
            </Label>
            <Input
              id={inputId}
              type={field.id === "api_key" ? "password" : "url"}
              autoComplete={field.id === "api_key" ? "new-password" : "off"}
              value={values[field.id] ?? ""}
              placeholder={
                field.configured ? LAUNCHER_COPY.configuredField : LAUNCHER_COPY.missingField
              }
              onChange={(event) =>
                setValues((current) => ({ ...current, [field.id]: event.target.value }))
              }
            />
          </div>
        );
      })}
      {error && <div className="text-[11px] text-foreground">{error}</div>}
      <Button type="submit" size="sm" disabled={saving || !hasValue}>
        {saving ? LAUNCHER_COPY.savingProvider : LAUNCHER_COPY.saveProvider}
      </Button>
    </form>
  );
}
