import type { SelectHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Select({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "flex h-10 w-full min-w-0 max-w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background transition-colors focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
