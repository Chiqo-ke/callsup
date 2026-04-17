import { cn } from "../../lib/utils";

type Variant = "online" | "offline" | "loading" | "default" | "warning";

const variants: Record<Variant, string> = {
  online: "bg-emerald-100 text-emerald-800 border-emerald-200",
  offline: "bg-red-100 text-red-700 border-red-200",
  loading: "bg-slate-100 text-slate-500 border-slate-200 animate-pulse",
  default: "bg-blue-100 text-blue-700 border-blue-200",
  warning: "bg-amber-100 text-amber-700 border-amber-200",
};

interface BadgeProps {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
