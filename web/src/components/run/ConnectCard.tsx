import { useState, type FormEvent } from "react";
import { api } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CONNECT_COPY } from "@/copy";
import { messageOf } from "@/lib/format";
import type { CatalogProvider } from "@/types";

interface ConnectCardProps {
  provider: CatalogProvider;
  onConnected: () => void | Promise<void>;
}

export function ConnectCard({ provider, onConnected }: ConnectCardProps) {
  const field = provider.fields[0];
  const fieldId = field?.id ?? "api_key";
  const isUrl = fieldId === "base_url";
  const envVar = field?.env_var;  // shown only as a tooltip — a name, never a value
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!value.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.saveProvider(provider.id, { [fieldId]: value.trim() });
      setValue("");
      await onConnected();
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="gap-3 border border-line bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <strong>{provider.label}</strong>
        <Badge variant="outline" className={provider.connected ? "border-verdict-reliable/50 text-verdict-reliable" : "text-faint"}>
          {provider.connected ? CONNECT_COPY.connected : isUrl ? CONNECT_COPY.url : CONNECT_COPY.pasteKey}
        </Badge>
      </div>
      {isUrl && <p className="text-xs text-faint">{CONNECT_COPY.mlxHint}</p>}
      <form className="flex flex-col gap-2 sm:flex-row" onSubmit={save}>
        <div className="grid flex-1 gap-1.5">
          <Label htmlFor={`connect-${provider.id}`} className="sr-only">
            {isUrl ? CONNECT_COPY.baseUrl : CONNECT_COPY.apiKey} — {provider.label}
          </Label>
          <Input
            id={`connect-${provider.id}`}
            type={isUrl ? "url" : "password"}
            autoComplete="off"
            title={envVar}
            placeholder={isUrl ? CONNECT_COPY.urlPlaceholder : CONNECT_COPY.keyPlaceholder}
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
        </div>
        <Button type="submit" disabled={saving || !value.trim()}>
          {saving ? CONNECT_COPY.saving : CONNECT_COPY.save}
        </Button>
      </form>
      {error && <p className="text-xs text-verdict-unreliable">{error}</p>}
    </Card>
  );
}
