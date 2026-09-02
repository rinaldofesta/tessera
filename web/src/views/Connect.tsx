import { ConnectCard } from "@/components/run/ConnectCard";
import { Skeleton } from "@/components/ui/skeleton";
import { CONNECT_COPY } from "@/copy";
import { useCatalog } from "@/hooks";

export default function Connect() {
  const { catalog, error, reload } = useCatalog();

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="font-display text-2xl font-bold tracking-tight">{CONNECT_COPY.title}</h1>
      <p className="mt-1 mb-5 text-sm text-muted-foreground">{CONNECT_COPY.subtitle}</p>
      {!catalog && !error && <Skeleton className="h-48 w-full" />}
      {error && <p className="text-sm text-verdict-unreliable">{error}</p>}
      {catalog && (
        <div className="grid gap-3">
          {catalog.providers.map((provider) => (
            <ConnectCard key={provider.id} provider={provider} onConnected={reload} />
          ))}
        </div>
      )}
    </div>
  );
}
