"use client";

import { useId } from "react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

import { cn } from "@/lib/utils";

/** Mini price sparkline used in the product table. */
export function Sparkline({ data, positive = true }: { data: number[]; positive?: boolean }) {
  const id = useId().replace(/:/g, "");
  const values = data.length >= 2 ? data : [0, 0];
  const color = positive ? "#00A651" : "#EF4444";
  const points = values.map((v, i) => ({ i, v }));

  return (
    <div className="h-8 w-20">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#spark-${id})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
