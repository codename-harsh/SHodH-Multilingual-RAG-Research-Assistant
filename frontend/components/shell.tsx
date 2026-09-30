"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, MessageSquare, Upload, BarChart3, Search } from "lucide-react";
import { Toaster } from "sonner";
import { ThemeToggle } from "@/components/theme-toggle";

const links = [
  ["/chat", "Ask", MessageSquare],
  ["/upload", "Upload", Upload],
  ["/docs", "Documents", FileText],
  ["/eval", "Evaluation", BarChart3],
] as const;

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 hidden w-56 border-r border-border px-4 py-5 md:block">
        <div className="flex items-center justify-between"><Link href="/" className="flex items-center gap-2 px-2 text-sm font-semibold tracking-tight"><span className="grid h-7 w-7 place-items-center rounded-md bg-foreground text-background">S</span> Shodh</Link><ThemeToggle /></div>
        <nav className="mt-10 space-y-1">
          {links.map(([href, label, Icon]) => <Link key={href} href={href} className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm ${pathname === href ? "bg-foreground/[.06] font-medium" : "text-foreground/60 hover:bg-foreground/[.04]"}`}><Icon size={16}/>{label}</Link>)}
        </nav>
        <div className="absolute bottom-5 left-6 right-6 text-[11px] leading-5 text-foreground/40">Multilingual retrieval<br/>with evidence, not vibes.</div>
      </aside>
      <main className="md:pl-56"><div className="mx-auto min-h-screen max-w-6xl px-5 py-6 md:px-10 md:py-8">{children}<footer className="mt-16 border-t border-border py-5 text-[11px] text-foreground/35">Built with Shodh · Evidence over decoration.</footer></div></main>
      <Toaster position="bottom-right" />
    </div>
  );
}
