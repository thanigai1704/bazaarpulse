"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { LiveEvent, PriceUpdateEvent } from "@/lib/types";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/live-updates";

/**
 * Subscribes to the BazaarPulse WebSocket live feed.
 * - Auto-reconnects with exponential backoff.
 * - Buffers recent events so a freshly-mounted page isn't blank.
 * - Returns the full event log + the latest events per product id.
 */
export function useLiveUpdates() {
  const [connected, setConnected] = useState(false);
  const [eventLog, setEventLog] = useState<LiveEvent[]>([]);
  const [latestByProduct, setLatestByProduct] = useState<Record<string, PriceUpdateEvent>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      retryRef.current = 0;
      setConnected(true);
    };

    ws.onmessage = (evt) => {
      try {
        const event = JSON.parse(evt.data) as LiveEvent;
        setEventLog((prev) => [...prev.slice(-80), event]);
        if (event.type === "price_update") {
          const update = event as PriceUpdateEvent;
          setLatestByProduct((prev) => ({ ...prev, [update.payload.product_id]: update }));
        }
      } catch {
        /* ignore malformed frames */
      }
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = Math.min(15000, 1000 * 2 ** retryRef.current);
      retryRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected, eventLog, latestByProduct };
}

/** Returns the freshest price for a product id (live updates win over REST). */
export function useLivePrice(productId: string, fallback: number) {
  const { latestByProduct } = useLiveUpdates();
  const update = latestByProduct[productId];
  return update ? update.payload.current_price : fallback;
}
