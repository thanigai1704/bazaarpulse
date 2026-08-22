import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
  {
    variants: {
      variant: {
        default: "bg-brand-light text-brand-dark ring-brand/20 dark:bg-brand/15 dark:text-brand",
        green: "bg-brand-light text-brand-dark ring-brand/20 dark:bg-brand/15 dark:text-brand",
        gray: "bg-secondary text-muted-foreground ring-border",
        red: "bg-red-50 text-red-600 ring-red-200 dark:bg-red-950/40 dark:text-red-400 dark:ring-red-900",
        amber: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:ring-amber-900",
        outline: "bg-transparent text-foreground ring-border",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
