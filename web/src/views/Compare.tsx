import { lazy, Suspense } from "react";
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
        <TabsContent value="adhoc"><AdHocTab /></TabsContent>
        <TabsContent value="experiments">
          <Suspense fallback={<Skeleton className="h-40 w-full" />}>
            <ExperimentsTab />
          </Suspense>
        </TabsContent>
      </Tabs>
    </div>
  );
}
