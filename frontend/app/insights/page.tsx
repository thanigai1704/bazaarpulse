"use client";

import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { MoversList } from "@/components/insights/movers-list";
import { SentimentLeaders } from "@/components/insights/sentiment-leaders";
import { AiSummaryCard } from "@/components/insights/ai-summary-card";
import type { MarketSummary, SentimentLeader, TrendingInsights } from "@/lib/types";

export default function InsightsPage() {
  const { data: trending, loading: moversLoading } = useApi<TrendingInsights>(
    () => api.trending(24),
    [],
    120000,
  );
  const { data: leaders, loading: leadersLoading } = useApi<SentimentLeader[]>(
    () => api.sentimentLeaders(),
    [],
    120000,
  );
  const { data: summary, loading: summaryLoading } = useApi<MarketSummary>(
    () => api.summary(),
    [],
    120000,
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Market Insights</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Price movers, sentiment leaders & AI-generated analysis across the tracked market.
        </p>
      </div>

      <div className="space-y-6">
        <AiSummaryCard data={summary} loading={summaryLoading} />
        <MoversList drops={trending?.biggest_drops ?? []} rises={trending?.biggest_rises ?? []} loading={moversLoading} />
        <SentimentLeaders data={leaders} loading={leadersLoading} />
      </div>
    </div>
  );
}
