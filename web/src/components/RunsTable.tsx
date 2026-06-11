import { StatusToken } from "@/components/term";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { fmtTs, pct, shortModel } from "@/lib/format";
import type { RunSummary } from "@/types";

export function RunsTable({ rows }: { rows: RunSummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="text-[10px] uppercase tracking-[0.15em]">when (utc)</TableHead>
          <TableHead className="text-[10px] uppercase tracking-[0.15em]">status</TableHead>
          <TableHead className="text-[10px] uppercase tracking-[0.15em]">model</TableHead>
          <TableHead className="hidden text-[10px] uppercase tracking-[0.15em] md:table-cell">org</TableHead>
          <TableHead className="hidden text-[10px] uppercase tracking-[0.15em] md:table-cell">engine</TableHead>
          <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">k</TableHead>
          <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">pass^k</TableHead>
          <TableHead className="text-right text-[10px] uppercase tracking-[0.15em]">mean</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.id} className="text-xs" title={r.error ?? undefined}>
            <TableCell className="tabular-nums text-muted-foreground">{fmtTs(r.created_at)}</TableCell>
            <TableCell><StatusToken status={r.status} /></TableCell>
            <TableCell className="max-w-[160px] truncate">{shortModel(r.model)}</TableCell>
            <TableCell className="hidden md:table-cell">{r.org}</TableCell>
            <TableCell className="hidden text-muted-foreground md:table-cell">{r.judge}</TableCell>
            <TableCell className="text-right tabular-nums">{r.epochs}</TableCell>
            <TableCell className="text-right font-bold tabular-nums">{pct(r.pass_k_rate)}</TableCell>
            <TableCell className="text-right tabular-nums text-muted-foreground">{pct(r.mean_rate)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
