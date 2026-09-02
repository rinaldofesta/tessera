import { useMemo } from "react";
import { Input } from "@/components/ui/input";
import { RUN_COPY } from "@/copy";
import { SELECT_CLASS } from "@/components/run/shared";
import type { CatalogModel, CatalogProvider } from "@/types";

const CUSTOM_MODEL = "__custom_model__";

interface ModelSelectProps {
  models: CatalogModel[];
  providers: CatalogProvider[];
  value: string;
  onChange: (value: string) => void;
}

export function ModelSelect({ models, providers, value, onChange }: ModelSelectProps) {
  const known = models.some((model) => model.id === value);
  const { groups, ungrouped } = useMemo(() => ({
    groups: providers.map((provider) => ({
      provider,
      models: models.filter((model) => model.provider === provider.id),
    })).filter((group) => group.models.length > 0),
    ungrouped: models.filter(
      (model) => !providers.some((provider) => provider.id === model.provider),
    ),
  }), [models, providers]);

  return (
    <span className="inline-grid gap-2">
      <select
        aria-label={RUN_COPY.modelLabel}
        className={SELECT_CLASS}
        value={known ? value : CUSTOM_MODEL}
        onChange={(event) => onChange(event.target.value === CUSTOM_MODEL ? "" : event.target.value)}
      >
        {groups.map(({ provider, models: rows }) => (
          <optgroup key={provider.id} label={provider.label}>
            {rows.map((model) => (
              <option key={model.id} value={model.id}>
                {model.label}{model.connected ? " · ●" : ""}
              </option>
            ))}
          </optgroup>
        ))}
        {ungrouped.map((model) => (
          <option key={model.id} value={model.id}>{model.label}</option>
        ))}
        <option value={CUSTOM_MODEL}>{RUN_COPY.customModel}</option>
      </select>
      {!known && (
        <Input
          aria-label={RUN_COPY.customModel}
          className="min-w-64 bg-raised font-mono"
          placeholder={RUN_COPY.customModelPlaceholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </span>
  );
}
