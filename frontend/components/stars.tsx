import { Star, StarHalf } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatRating } from "@/lib/format";

export function Stars({ rating, className }: { rating: number; className?: string }) {
  const value = Math.max(0, Math.min(5, rating));
  const full = Math.floor(value);
  const half = value - full >= 0.5;
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)}>
      {Array.from({ length: 5 }).map((_, i) => {
        if (i < full) return <Star key={i} className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />;
        if (i === full && half)
          return <StarHalf key={i} className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />;
        return <Star key={i} className="h-3.5 w-3.5 text-muted-foreground/40" />;
      })}
    </span>
  );
}

export function RatingLabel({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm">
      <span className="rounded bg-brand px-1.5 py-0.5 text-xs font-semibold text-white">
        {formatRating(rating)}
      </span>
      <span className="text-xs text-muted-foreground">/5</span>
    </span>
  );
}
