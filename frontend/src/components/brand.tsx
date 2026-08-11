import Link from "next/link";
import { GraduationCap } from "lucide-react";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link href="/" className={`inline-flex items-center gap-2.5 ${className}`}>
      <span
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
        style={{ background: "linear-gradient(135deg, var(--color-aurora-600), var(--color-aurora-900))" }}
        aria-hidden
      >
        <GraduationCap className="h-4.5 w-4.5 text-white" strokeWidth={2.25} />
      </span>
      <span className="display text-lg tracking-tight">EduBridge</span>
    </Link>
  );
}
