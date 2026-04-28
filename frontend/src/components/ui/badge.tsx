import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export type BadgeVariant =
  | "default"
  | "secondary"
  | "outline"
  | "success"
  | "warning"
  | "danger";

const variants: Record<BadgeVariant, string> = {
  default: "bg-primary text-primary-foreground",
  secondary: "bg-secondary text-secondary-foreground",
  outline: "border border-border bg-background",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  warning: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  danger: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
};

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex min-w-0 items-center rounded-md px-2 py-1 text-xs font-medium leading-none",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
