"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, History, Send, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type Doc = {
  id: string;
  filename: string;
  n_chunks: number;
  uploaded_at: string;
  status: string;
};

type Citation = { page: number; chunk_id: string; text_snippet: string };
type Message = { role: "user" | "assistant"; content: string; citations?: Citation[] };
type Log = {
  id: string;
  question: string;
  answer: string;
  doc_id?: string | null;
  citations?: Citation[];
  created_at: string;
};

export default function ChatPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [doc, setDoc] = useState("");
  const [q, setQ] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<Log[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    api<Doc[]>("/documents").then(setDocs).catch((error) => toast.error(error.message));
    api<Log[]>("/query_logs").then(setHistory).catch(() => {});
  }, []);

  useEffect(() => {
    if (!showHistory) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowHistory(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [showHistory]);

  const selected = useMemo(() => docs.find((item) => item.id === doc), [docs, doc]);

  async function ask() {
    if (!q.trim() || !doc) return toast.error("Choose a document first");
    const question = q.trim();
    setQ("");
    setMessages((current) => [...current, { role: "user", content: question }]);
    setLoading(true);
    try {
      const result = await api<{
        answer: string;
        citations: Citation[];
        model: string;
        latency_ms: number;
        detected_language: string;
      }>("/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, doc_id: doc }),
      });
      setMessages((current) => [
        ...current,
        { role: "assistant", content: result.answer, citations: result.citations },
      ]);
      setHistory((current) => [
        {
          id: crypto.randomUUID(),
          question,
          answer: result.answer,
          doc_id: doc,
          citations: result.citations,
          created_at: new Date().toISOString(),
        },
        ...current,
      ]);
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="flex h-[calc(100vh-4rem)] min-h-[650px] gap-5 py-3">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-[.16em] text-foreground/40">Research</div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">Ask Shodh</h1>
          </div>
          <button
            aria-controls="query-history"
            aria-expanded={showHistory}
            className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-xs"
            onClick={() => setShowHistory((visible) => !visible)}
            type="button"
          >
            <History size={14} /> History
          </button>
        </div>

        <div className="mb-4">
          <select
            value={doc}
            onChange={(event) => setDoc(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none"
          >
            <option value="">Select a document</option>
            {docs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.filename} · {item.n_chunks} chunks
              </option>
            ))}
          </select>
        </div>

        <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex-1 space-y-5 overflow-y-auto p-5">
            {messages.length === 0 ? (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <div className="text-sm font-medium">Ask a precise question.</div>
                  <div className="mt-2 max-w-sm text-xs leading-5 text-foreground/45">
                    Answers are grounded in the selected document and include page-level evidence.
                  </div>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={message.role === "user" ? "ml-auto max-w-[80%]" : "max-w-[90%]"}
                >
                  <div
                    className={
                      message.role === "user"
                        ? "rounded-xl bg-foreground px-4 py-3 text-sm text-background"
                        : "text-sm leading-7"
                    }
                  >
                    {message.content}
                  </div>
                  {message.citations && (
                    <div className="mt-3 space-y-2">
                      {message.citations.map((citation, citationIndex) => (
                        <details key={citationIndex} className="group rounded-lg border border-border">
                          <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-xs">
                            <span>
                              <Badge>p. {citation.page}</Badge>
                              <span className="ml-2 text-foreground/50">{citation.chunk_id}</span>
                            </span>
                            <ChevronDown size={14} className="transition-transform group-open:rotate-180" />
                          </summary>
                          <div className="border-t border-border px-3 py-3 text-xs leading-5 text-foreground/60">
                            {citation.text_snippet}
                          </div>
                        </details>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
            {loading && (
              <div className="space-y-2">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            )}
          </div>
          <div className="border-t border-border p-3">
            <div className="flex gap-2">
              <input
                value={q}
                onChange={(event) => setQ(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && void ask()}
                disabled={!doc || loading}
                placeholder={selected ? `Ask about ${selected.filename}` : "Select a document first"}
                className="h-11 flex-1 rounded-md border border-border bg-transparent px-3 text-sm outline-none"
              />
              <button
                onClick={() => void ask()}
                disabled={!doc || loading}
                className="grid h-11 w-11 place-items-center rounded-md bg-foreground text-background disabled:opacity-30"
                type="button"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </Card>
      </div>

      {showHistory && (
        <>
          <button
            aria-label="Close query history"
            className="fixed inset-0 z-40 bg-black/30 lg:hidden"
            onClick={() => setShowHistory(false)}
            type="button"
          />
          <aside
            id="query-history"
            aria-label="Recent queries"
            className="fixed inset-y-0 right-0 z-50 w-[min(22rem,88vw)] overflow-y-auto border-l border-border bg-background p-4 shadow-xl lg:static lg:z-auto lg:w-72 lg:shrink-0 lg:overflow-visible lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="text-xs font-medium uppercase tracking-[.16em] text-foreground/40">
                Recent queries
              </div>
              <button
                aria-label="Close query history"
                className="rounded-md p-1 text-foreground/50 hover:bg-foreground/[.05] lg:hidden"
                onClick={() => setShowHistory(false)}
                type="button"
              >
                <X size={16} />
              </button>
            </div>
            <div className="space-y-2">
              {history.length === 0 ? (
                <div className="text-xs text-foreground/40">No queries yet.</div>
              ) : (
                history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      if (item.doc_id) setDoc(item.doc_id);
                      setQ("");
                      setMessages([
                        { role: "user", content: item.question },
                        { role: "assistant", content: item.answer, citations: item.citations },
                      ]);
                      setShowHistory(false);
                    }}
                    className="w-full rounded-lg border border-border p-3 text-left hover:bg-foreground/[.02]"
                    type="button"
                  >
                    <div className="text-xs font-medium leading-5">{item.question}</div>
                    <div className="mt-2 line-clamp-2 text-xs leading-5 text-foreground/55">
                      {item.answer}
                    </div>
                    <div className="mt-2 text-[10px] text-foreground/40">
                      {new Date(item.created_at).toLocaleString()}
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>
        </>
      )}
    </section>
  );
}
