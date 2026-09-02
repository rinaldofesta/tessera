import { lazy, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/viz/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { COMPARE_COPY } from "@/copy";
import AdHocTab from "./compare/AdHocTab";

const ExperimentsTab = lazy(() => import("./compare/ExperimentsTab"));

export default function Compare() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "experiments" ? "experiments" : "adhoc";

  // Base UI's Tabs.Panel unmounts an inactive panel by default, which would wipe
  // AdHocTab's/ExperimentsTab's in-progress state (selection, edited fields) on every
  // switch and re-seed them from the URL as it was when the tab was first opened.
  // Keep a panel mounted once it's been visited — but only once, so the tab that's
  // never opened still doesn't pay for its lazy chunk or start its polling effects.
  const [visited, setVisited] = useState<ReadonlySet<string>>(() => new Set([tab]));
  useEffect(() => {
    setVisited((current) => (current.has(tab) ? current : new Set(current).add(tab)));
  }, [tab]);

  return (
    <div>
      <PageHeader eyebrow={COMPARE_COPY.eyebrow} title={COMPARE_COPY.title} subtitle={COMPARE_COPY.subtitle} />
      <Tabs
        value={tab}
        onValueChange={(next) =>
          setParams((current) => {
            const p = new URLSearchParams(current);
            if (next === "experiments") p.set("tab", "experiments");
            else p.delete("tab");
            return p;
          })
        }
      >
        <TabsList>
          <TabsTrigger value="adhoc">{COMPARE_COPY.tabAdHoc}</TabsTrigger>
          <TabsTrigger value="experiments">{COMPARE_COPY.tabExperiments}</TabsTrigger>
        </TabsList>
        <TabsContent value="adhoc" keepMounted={visited.has("adhoc")}><AdHocTab /></TabsContent>
        <TabsContent value="experiments" keepMounted={visited.has("experiments")}>
          <Suspense fallback={<Skeleton className="h-40 w-full" />}>
            <ExperimentsTab />
          </Suspense>
        </TabsContent>
      </Tabs>
    </div>
  );
}
