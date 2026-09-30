import "./globals.css";
import type { Metadata } from "next";
import { AuthGate } from "@/components/auth-gate";
import { Shell } from "@/components/shell";

export const metadata: Metadata = { title: "Shodh", description: "Multilingual RAG research assistant" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><AuthGate><Shell>{children}</Shell></AuthGate></body></html>;
}
