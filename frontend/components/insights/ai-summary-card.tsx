"use client";

import { Bot, Sparkles } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { timeAgo } from "@/lib/format";
import type { MarketSummary } from "@/lib/types";

export function AiSummaryCard({ data, loading }: { data: MarketSummary | null; loading: boolean }) {
  return (
    <div className="rounded-xl border-2 border-brand/50 bg-brand-light/50 p-6 dark:bg-brand/10">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white">
          <Bot className="h-4 w-4" />
        </span>
        <div>
          <p className="flex items-center gap-1.5 text-sm font-semibold">
            AI Weekly Summary <Sparkles className="h-3.5 w-3.5 text-brand" />
          </p>
          {data && <p className="text-xs text-muted-foreground">Generated {timeAgo(data.generated_at)}</p>}
        </div>
      </div>

      {loading ? (
        <div className="mt-4 space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : data ? (
        <>
          <p className="mt-4 text-sm leading-relaxed text-foreground/90">{data.summary_text}</p>
          {data.movers_json.length > 0 && (
            <p className="mt-3 text-xs text-muted-foreground">
              Key movers:{" "}
              {data.movers_json
                .slice(0, 3)
                .map((m) => `${m.name} (${m.change_pct > 0 ? "+" : ""}${m.change_pct}%)`)
                .join(" · ")}
            </p>
          )}
        </>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">
          The AI summary is generated on the next refresh cycle. Keep the dashboard open for a few minutes.
        </p>
      )}
    </div>
  );
}
