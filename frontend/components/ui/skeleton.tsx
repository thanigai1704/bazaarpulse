import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-secondary/80 relative overflow-hidden",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
