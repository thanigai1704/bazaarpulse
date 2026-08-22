import { Smile, Meh, Frown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { SentimentLabel } from "@/lib/types";

const META: Record<SentimentLabel, { icon: typeof Smile; cls: "green" | "gray" | "red"; label: string }> = {
  positive: { icon: Smile, cls: "green", label: "Positive" },
  neutral: { icon: Meh, cls: "gray", label: "Neutral" },
  negative: { icon: Frown, cls: "red", label: "Negative" },
};

export function SentimentBadge({ label, size = "sm" }: { label: SentimentLabel; size?: "sm" | "md" }) {
  const meta = META[label] ?? META.neutral;
  const Icon = meta.icon;
  return (
    <Badge variant={meta.cls} className={size === "md" ? "px-2.5 py-1 text-xs" : ""}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </Badge>
  );
}

/** Emoji indicator for the KPI card (😊/😐/😞). */
export function SentimentEmoji({ label }: { label: SentimentLabel }) {
  if (label === "positive") return <span aria-label="positive">😊</span>;
  if (label === "negative") return <span aria-label="negative">😞</span>;
  return <span aria-label="neutral">😐</span>;
}
