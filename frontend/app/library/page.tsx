"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "../../lib/api";

type Work = { title: string; year: number | null; doi: string | null; authors: string[]; abstract: string; openalex_url: string };
type SearchResult = { query: string; provider: string; results: Work[]; knowledge_maps_url: string };

export default function LibraryPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function search(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await api<SearchResult>(`/api/v1/library/search?q=${encodeURIComponent(query)}&limit=10`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "文献检索失败");
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv() {
    try {
      const response = await fetch(`/api/v1/library/export?q=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` },
      });
      if (!response.ok) throw new Error((await response.json()).detail ?? "导出失败");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = "文献检索.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "导出失败");
    }
  }

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <h1>文献库</h1>
    <p>通过 OpenAlex 公共学术目录检索真实书目信息与摘要；可打开 Open Knowledge Maps 查看主题知识地图。</p>
    <section className="subPageCard">
      <form className="inlineForm" onSubmit={search}>
        <input aria-label="专业词或主题" required minLength={2} maxLength={300} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入专业词或研究主题" />
        <button disabled={busy}>{busy ? "检索中…" : "检索文献"}</button>
      </form>
      {result && <div className="libraryToolbar"><span>{result.provider} · {result.results.length} 条记录</span><button onClick={exportCsv}>导出 CSV</button><a href={result.knowledge_maps_url} target="_blank" rel="noreferrer">打开 Open Knowledge Maps ↗</a></div>}
      {error && <p className="inlineError" role="alert">{error}</p>}
      {result?.results.map((work) => <article className="workCard" key={work.openalex_url}>
        <h3>{work.title}</h3>
        <p>{work.year ?? "年份未提供"} · {work.authors.slice(0, 5).join(", ") || "作者未提供"}</p>
        {work.doi && <a href={work.doi} target="_blank" rel="noreferrer">{work.doi}</a>}
        <p className="abstractText">{work.abstract ? `${work.abstract.slice(0, 900)}${work.abstract.length > 900 ? "…" : ""}` : "该记录未提供摘要，不能生成摘要简介。"}</p>
        <a href={work.openalex_url} target="_blank" rel="noreferrer">OpenAlex 记录 ↗</a>
      </article>)}
      {result?.results.length === 0 && <p>没有找到匹配记录，可尝试更宽泛的专业词。</p>}
    </section>
  </main>;
}
