"use client";

import { cn } from "@/lib/utils";

const SIZE_CLASSES = ["text-sm", "text-base", "text-lg", "text-xl", "text-2xl"];
const INTENSITIES = [
  "text-muted-foreground",
  "text-muted-foreground",
  "text-foreground/70",
  "text-foreground",
  "text-brand",
];

/** Simple deterministic tag cloud of AI-extracted review keywords. */
export function WordCloud({ keywords }: { keywords: string[] }) {
  const words = keywords.slice(0, 8);
  if (words.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Keywords appear here after the next AI insight refresh.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {words.map((word, i) => {
        const tier = i % SIZE_CLASSES.length;
        return (
          <span
            key={word}
            className={cn(
              "rounded-full border px-2.5 py-1 font-medium",
              SIZE_CLASSES[tier],
              INTENSITIES[i % 3 === 0 ? 4 : tier],
            )}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
}
