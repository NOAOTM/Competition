"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../../lib/api";

type Work = { title: string; year: number | null; doi: string | null; authors: string[]; abstract: string; openalex_url: string };
type SearchResult = { query: string; provider: string; results: Work[]; knowledge_maps_url: string };

export default function LibraryPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<string[]>([]);
  const [view, setView] = useState<"all" | "saved" | "abstracts">("all");

  useEffect(() => {
    try {
      const parsed: unknown = JSON.parse(localStorage.getItem("library-saved") ?? "[]");
      setSaved(Array.isArray(parsed) && parsed.every((item) => typeof item === "string") ? parsed : []);
    }
    catch { setSaved([]); }
  }, []);

  async function runSearch(searchQuery: string) {
    setBusy(true);
    setError("");
    try {
      setResult(await api<SearchResult>(`/api/v1/library/search?q=${encodeURIComponent(searchQuery)}&limit=10`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "文献检索失败");
    } finally {
      setBusy(false);
    }
  }

  async function search(event: FormEvent) {
    event.preventDefault();
    await runSearch(query);
  }

  function toggleSaved(url: string) {
    setSaved((current) => {
      const next = current.includes(url) ? current.filter((item) => item !== url) : [...current, url];
      localStorage.setItem("library-saved", JSON.stringify(next));
      return next;
    });
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

  const visibleWorks = (result?.results ?? []).filter((work) => {
    if (view === "saved") return saved.includes(work.openalex_url);
    if (view === "abstracts") return Boolean(work.abstract);
    return true;
  });

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <header className="libraryHero"><div><span className="libraryEyebrow">OPEN ACADEMIC DISCOVERY</span><h1>文献发现</h1><p>从真实学术记录出发，探索研究主题、重要论文与知识脉络。</p></div><div className="libraryHeroStamp">研究<br />有据可循</div></header>
    <section className="librarySearchPanel">
      <form className="inlineForm librarySearchForm" onSubmit={search}>
        <span aria-hidden="true">⌕</span><input aria-label="专业词或主题" required minLength={2} maxLength={300} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入专业词、作者或研究主题" />
        <button disabled={busy}>{busy ? "正在检索…" : "搜索文献"}</button>
      </form>
      <div className="libraryTopics"><span>试试这些主题</span>{["人工智能教育", "气候变化", "计算机视觉", "心理健康"].map((topic) =>
        <button type="button" key={topic} onClick={() => { setQuery(topic); void runSearch(topic); }}>{topic}</button>)}</div>
    </section>
    <section className="libraryResults">
      <div className="librarySectionHeading"><div><span>RESEARCH COLLECTION</span><h2>{result ? `「${result.query}」的研究` : "发现值得阅读的研究"}</h2></div>
        {result && <div className="libraryControls"><button onClick={exportCsv}>导出 CSV ↓</button><a href={result.knowledge_maps_url} target="_blank" rel="noreferrer">主题地图 ↗</a></div>}
      </div>
      {result && <div className="libraryFilterBar"><span>{result.provider} · {result.results.length} 条真实记录</span><div>
        <button className={view === "all" ? "active" : ""} onClick={() => setView("all")}>全部</button>
        <button className={view === "abstracts" ? "active" : ""} onClick={() => setView("abstracts")}>含摘要</button>
        <button className={view === "saved" ? "active" : ""} onClick={() => setView("saved")}>已收藏 {saved.length ? `(${saved.length})` : ""}</button>
      </div></div>}
      {error && <p className="inlineError" role="alert">{error}</p>}
      {busy && <div className="libraryLoading" role="status"><span className="spinner" />正在查询 OpenAlex 学术目录…</div>}
      {!result && !busy && <div className="libraryEmpty"><span>✦</span><b>从一个研究问题开始</b><p>检索内容来自 OpenAlex 公共学术目录；摘要仅在原始记录提供时展示。</p></div>}
      <div className="libraryWorkList">{visibleWorks.map((work, index) => <article className="libraryWorkCard" key={work.openalex_url}>
        <div className="libraryWorkIndex">{String(index + 1).padStart(2, "0")}</div><div className="libraryWorkContent">
          <div className="libraryWorkMeta"><span>{work.year ?? "年份未提供"}</span><span>{work.authors.slice(0, 3).join(" · ") || "作者未提供"}</span></div>
          <h3>{work.title}</h3>
          <p className="libraryAbstract">{work.abstract ? `${work.abstract.slice(0, 700)}${work.abstract.length > 700 ? "…" : ""}` : "原始记录未提供摘要。"}</p>
          <div className="libraryWorkActions">{work.doi && <a href={work.doi} target="_blank" rel="noreferrer">DOI ↗</a>}<a href={work.openalex_url} target="_blank" rel="noreferrer">查看 OpenAlex 记录 ↗</a></div>
        </div><button className={saved.includes(work.openalex_url) ? "librarySave saved" : "librarySave"} onClick={() => toggleSaved(work.openalex_url)} aria-label={saved.includes(work.openalex_url) ? "取消收藏" : "收藏文献"} title={saved.includes(work.openalex_url) ? "取消收藏" : "收藏"}>{saved.includes(work.openalex_url) ? "★" : "☆"}</button>
      </article>)}</div>
      {result && !visibleWorks.length && <div className="libraryEmpty"><span>⌕</span><b>{view === "saved" ? "当前结果中没有已收藏文献" : "没有符合筛选条件的记录"}</b><p>切换筛选条件，或检索更多主题。</p></div>}
    </section>
  </main>;
}
