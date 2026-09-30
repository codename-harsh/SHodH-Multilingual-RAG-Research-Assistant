"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

export function AuthGate({ children }: { children: React.ReactNode }) {
  // This is a public UI switch only. The shared API key is configured on the
  // backend and must never be embedded in the browser bundle.
  const required = process.env.NEXT_PUBLIC_REQUIRE_API_KEY === "true";
  const [ready, setReady] = useState(!required);
  const [key, setKey] = useState("");

  useEffect(() => {
    if (required && localStorage.getItem("shodh-api-key")) setReady(true);
  }, [required]);

  if (!required || ready) return <>{children}</>;
  return <main className="grid min-h-screen place-items-center p-6"><div className="w-full max-w-sm rounded-2xl border border-border p-6"><div className="mb-6 text-lg font-semibold">Shodh access</div><p className="mb-4 text-sm text-foreground/60">Enter the local API key configured for this environment.</p><input className="mb-3 h-10 w-full rounded-md border border-border bg-transparent px-3 text-sm outline-none" value={key} onChange={e => setKey(e.target.value)} placeholder="API key" type="password"/><Button className="w-full" onClick={() => { localStorage.setItem("shodh-api-key", key); setReady(true); }}>Continue</Button></div></main>;
}
