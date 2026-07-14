import React from "react";
import { Input } from "@/components/ui/input";
import type { ValidationError } from "@/types";

/** Shared form primitives for the dataset editor and the scenario wizard — labeled
    text inputs and the validation-issues list, in the same terminal aesthetic as
    the display widgets in `term.tsx`. */

export function FieldLabel({ children }: React.PropsWithChildren) {
  return (
    <span className="mb-0.5 block text-[10px] uppercase tracking-[0.15em] text-muted-foreground">{children}</span>
  );
}

export function Field({ label, value, placeholder, onChange }: {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (v: string) => void;
}) {
  return (
    <label>
      <FieldLabel>{label}</FieldLabel>
      <Input value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

export function ValidationErrors({ errors }: { errors: ValidationError[] }) {
  return (
    <ul className="space-y-1.5 text-xs">
      {errors.map((e, i) => (
        <li key={i} className="border-l-2 border-foreground pl-2">
          <div className="text-[10px] text-muted-foreground">{e.location}</div>
          {e.message}
        </li>
      ))}
    </ul>
  );
}
