"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function Dialog({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onMouseDown={onClose}>
      <div className={cn("w-full max-w-lg rounded-2xl border border-border bg-background p-6 shadow-2xl")} onMouseDown={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">{title}</h2><button onClick={onClose} aria-label="Close">×</button></div>
        {children}
      </div>
    </div>
  );
}
