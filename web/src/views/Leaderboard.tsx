import { ExternalLink } from "lucide-react";

const LEADERBOARD_URL =
  "https://github.com/rinaldofesta/tessera/blob/main/docs/leaderboard.md";

export default function Leaderboard() {
  return (
    <section className="max-w-3xl">
      <p className="font-mono text-xs font-medium uppercase tracking-[0.16em] text-primary">
        Leaderboard
      </p>
      <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-foreground">
        Public reliability results
      </h1>
      <div className="mt-6 rounded-lg border border-border bg-card p-6">
        <p className="max-w-2xl leading-7 text-muted-foreground">
          The public leaderboard is generated from a committed manifest and published with the
          project docs. {" "}
          <a
            href={LEADERBOARD_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline"
          >
            View the public leaderboard
            <ExternalLink aria-hidden="true" className="size-3.5" />
          </a>
          . The in-app leaderboard view arrives in a later phase.
        </p>
      </div>
    </section>
  );
}
