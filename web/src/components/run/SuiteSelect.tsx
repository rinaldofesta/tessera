import { useNavigate } from "react-router-dom";
import { RUN_COPY } from "@/copy";
import { SELECT_CLASS } from "@/components/run/shared";
import type { CatalogSuite } from "@/types";

const CUSTOM_SUITE = "__custom_suite__";

interface SuiteSelectProps {
  suites: CatalogSuite[];
  value: string;
  onChange: (value: string) => void;
}

export function SuiteSelect({ suites, value, onChange }: SuiteSelectProps) {
  const navigate = useNavigate();
  return (
    <select
      aria-label={RUN_COPY.suiteLabel}
      className={SELECT_CLASS}
      value={value}
      onChange={(event) => {
        if (event.target.value === CUSTOM_SUITE) navigate("/suites");
        else onChange(event.target.value);
      }}
    >
      {suites.map((suite) => (
        <option key={suite.name} value={suite.name}>{suite.label}</option>
      ))}
      <option value={CUSTOM_SUITE}>{RUN_COPY.customSuite}</option>
    </select>
  );
}
