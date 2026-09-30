import Link from "next/link";
import { ArrowUpRight, Search } from "lucide-react";

export default function Home() {
  return <main className="flex min-h-[calc(100vh-4rem)] flex-col justify-center py-20">
    <div className="max-w-3xl">
      <div className="mb-8 flex items-center gap-2 text-xs font-medium uppercase tracking-[.18em] text-foreground/45"><span className="h-1.5 w-1.5 rounded-full bg-foreground"/> Research workspace</div>
      <h1 className="text-5xl font-semibold tracking-[-.04em] md:text-7xl">Ask your documents<br/><span className="text-foreground/35">for evidence.</span></h1>
      <p className="mt-7 max-w-xl text-base leading-7 text-foreground/60">Shodh turns multilingual documents into a searchable research corpus, then shows you exactly which pages support an answer.</p>
      <div className="mt-10 flex flex-wrap gap-3"><Link href="/upload" className="inline-flex h-11 items-center gap-2 rounded-md bg-foreground px-5 text-sm font-medium text-background">Upload <ArrowUpRight size={15}/></Link><Link href="/chat" className="inline-flex h-11 items-center gap-2 rounded-md border border-border px-5 text-sm font-medium">Ask <Search size={15}/></Link></div>
    </div>
    <div className="mt-24 grid max-w-4xl grid-cols-1 border-y border-border md:grid-cols-3"><div className="border-b border-border p-5 md:border-b-0 md:border-r"><div className="text-xs text-foreground/40">01</div><div className="mt-8 text-sm font-medium">Hybrid retrieval</div><p className="mt-2 text-xs leading-5 text-foreground/50">Dense semantics + BM25 sparse matching.</p></div><div className="border-b border-border p-5 md:border-b-0 md:border-r"><div className="text-xs text-foreground/40">02</div><div className="mt-8 text-sm font-medium">Evidence-first answers</div><p className="mt-2 text-xs leading-5 text-foreground/50">Page and chunk citations stay attached to the response.</p></div><div className="p-5"><div className="text-xs text-foreground/40">03</div><div className="mt-8 text-sm font-medium">Multilingual by design</div><p className="mt-2 text-xs leading-5 text-foreground/50">Ask in English, Hindi, or another supported language.</p></div></div>
  </main>;
}
