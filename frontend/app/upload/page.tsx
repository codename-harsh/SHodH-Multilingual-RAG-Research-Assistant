"use client";

import { useRef, useState } from "react";
import { CheckCircle2, FileUp, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { uploadUrl, api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function UploadPage() {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  async function submit(selected: File) {
    setFile(selected); setProgress(0); setStatus("uploading");
    const xhr = new XMLHttpRequest();
    xhr.open("POST", uploadUrl());
    const key = localStorage.getItem("shodh-api-key"); if (key) xhr.setRequestHeader("X-API-Key", key);
    xhr.upload.onprogress = e => { if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100)); };
    xhr.onerror = () => { setStatus("failed"); toast.error("Upload failed"); };
    xhr.onload = async () => {
      if (xhr.status >= 300) { setStatus("failed"); toast.error(xhr.responseText || "Upload failed"); return; }
      const data = JSON.parse(xhr.responseText); setJobId(data.job_id); setStatus("processing");
      const poll = async () => {
        try {
          const result = await api<{status: string; n_chunks: number; error?: string}>(`/ingest/${data.job_id}`);
          setStatus(result.status);
          if (result.status === "complete") { toast.success(`Indexed ${result.n_chunks} chunks`); return; }
          if (result.status === "failed") { toast.error(result.error || "Ingestion failed"); return; }
          window.setTimeout(() => { void poll(); }, 1200);
        } catch (error) {
          setStatus("failed");
          toast.error((error as Error).message || "Could not read job status");
        }
      };
      void poll();
    };
    const form = new FormData(); form.append("file", selected); xhr.send(form);
  }

  return <section className="py-8"><div className="mb-10"><div className="text-xs uppercase tracking-[.16em] text-foreground/40">Corpus</div><h1 className="mt-2 text-3xl font-semibold tracking-tight">Upload a document</h1><p className="mt-2 text-sm text-foreground/55">PDFs are parsed page by page and indexed for hybrid retrieval.</p></div>
    <Card className="max-w-2xl p-3"><button onClick={() => input.current?.click()} className="flex min-h-72 w-full flex-col items-center justify-center rounded-lg border border-dashed border-border px-6 text-center hover:bg-foreground/[.02]" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); const f=e.dataTransfer.files[0]; if(f?.type === "application/pdf") submit(f); else toast.error("PDF files only"); }}><input ref={input} type="file" accept="application/pdf" hidden onChange={e => {const f=e.target.files?.[0]; if(f) submit(f)}}/><div className="grid h-12 w-12 place-items-center rounded-xl border border-border"><FileUp size={20}/></div><div className="mt-5 text-sm font-medium">Drop a PDF here or choose a file</div><div className="mt-1 text-xs text-foreground/45">The original file is processed locally by the ingestion worker.</div></button></Card>
    {file && <Card className="mt-4 max-w-2xl p-5"><div className="flex items-center justify-between"><div><div className="text-sm font-medium">{file.name}</div><div className="mt-1 text-xs text-foreground/45">{(file.size/1024/1024).toFixed(2)} MB</div></div><Badge>{status}</Badge></div><div className="mt-5 h-1.5 overflow-hidden rounded-full bg-foreground/[.07]"><div className="h-full bg-foreground transition-all" style={{width: `${status === "complete" ? 100 : progress}%`}}/></div><div className="mt-3 flex items-center gap-2 text-xs text-foreground/45">{status === "processing" && <Loader2 className="animate-spin" size={13}/>} {status === "complete" && <CheckCircle2 size={13}/>} {jobId ? `Job ${jobId.slice(0, 8)}…` : `${progress}% uploaded`}</div></Card>}
  </section>;
}
