import { Activity, BrainCircuit, Bell, TrendingUp, ArrowRight, IndianRupee } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Activity,
    title: "Live Price Tracking",
    body: "Prices for 38+ smartphones, laptops and appliances streamed every 15 minutes — like an NSE ticker for Flipkart & Amazon.in.",
  },
  {
    icon: BrainCircuit,
    title: "AI Sentiment Analysis",
    body: "GPT-4o-mini reads customer reviews, tags them Positive / Neutral / Negative and summarises what the market really thinks.",
  },
  {
    icon: Bell,
    title: "Smart Alerts",
    body: "Spot the biggest drops before the sale ends. Festival-sale patterns (Big Billion Days, Great Indian Festival) surface automatically.",
  },
];

export function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 opacity-40 dark:opacity-20"
          style={{
            background:
              "radial-gradient(600px 300px at 20% 0%, rgba(0,166,81,0.12), transparent), radial-gradient(500px 260px at 85% 10%, rgba(29,185,84,0.10), transparent)",
          }}
        />
        <div className="relative mx-auto max-w-7xl px-4 py-20 text-center sm:px-6 sm:py-28">
          <span className="inline-flex items-center gap-2 rounded-full border border-brand/30 bg-brand-light px-3 py-1 text-xs font-medium text-brand-dark dark:bg-brand/10 dark:text-brand">
            <IndianRupee className="h-3 w-3" />
            Built for the Indian market · Flipkart + Amazon.in
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
            Track India&apos;s Market in{" "}
            <span className="text-brand">Real-Time</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            BazaarPulse watches e-commerce prices and customer sentiment across smartphones,
            laptops and home appliances — with AI-powered insights you can trust.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href="/dashboard">
                Explore Live Dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/insights">Market Insights</Link>
            </Button>
          </div>
          <p className="mt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <TrendingUp className="h-4 w-4 text-brand" />
            Prices update automatically — no refresh needed.
          </p>
        </div>
      </section>

      {/* Feature cards */}
      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="transition-shadow hover:shadow-lift">
              <CardContent className="pt-6">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-light text-brand dark:bg-brand/15">
                  <feature.icon className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{feature.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="border-t bg-secondary/50">
        <div className="mx-auto max-w-7xl px-4 py-16 text-center sm:px-6">
          <h2 className="text-2xl font-bold sm:text-3xl">See the market move, live.</h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Open the dashboard to watch prices and sentiment shift in real time over WebSocket —
            no page reloads.
          </p>
          <Button asChild size="lg" className="mt-6">
            <Link href="/dashboard">Open Live Dashboard</Link>
          </Button>
        </div>
      </section>
    </>
  );
}
