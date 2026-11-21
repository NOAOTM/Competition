"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "../../lib/api";

type Article = { title: string; year: number | null; authors: string[]; abstract: string; doi: string | null; openalex_url: string };
type Result = { query: string; provider: string; results: Article[] };

const topics = ["人工智能", "生命科学", "气候变化", "材料科学", "心理学", "机器人"];

export default function FrontierPage() {
  const [query, setQuery] = useState("人工智能");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function explore(term: string) {
    setBusy(true);
    setError("");
    try {
      setResult(await api<Result>(`/api/v1/library/search?q=${encodeURIComponent(term)}&limit=10`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "前沿文献加载失败");
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void explore(query);
  }

  return <main className="frontierPage">
    <header className="frontierMasthead"><Link href="/" className="backLink">← 真知 Agent</Link><span>研究 · 观点 · 发现</span><Link href="/library">进入文献库 ↗</Link></header>
    <div className="frontierLayout">
      <section className="frontierMain">
        <div className="frontierBrand"><span>真知 · 知识前沿</span><h1>让研究灵感<br /><em>持续发生</em></h1><p>从公开学术文献中发现新研究与新问题。每条内容均来自 OpenAlex 原始书目记录。</p></div>
        <form className="frontierSearch" onSubmit={submit}><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="搜索研究主题" placeholder="搜索一个主题，开启探索" /><button disabled={busy}>{busy ? "加载中…" : "探索 →"}</button></form>
        <nav className="frontierTopics" aria-label="研究主题">{topics.map((topic) => <button key={topic} className={query === topic ? "active" : ""} onClick={() => { setQuery(topic); void explore(topic); }}>{topic}</button>)}</nav>
        <div className="frontierFeedHeading"><div><span>OPEN ACADEMIC FEED</span><h2>{result ? `关于「${result.query}」` : "研究动态"}</h2></div>{result && <span>{result.provider} · {result.results.length} 条记录</span>}</div>
        {error && <p className="inlineError" role="alert">{error}</p>}
        {busy && <div className="libraryLoading" role="status"><span className="spinner" />正在从公开学术目录获取记录…</div>}
        {!result && !busy && <div className="frontierIntro"><b>知识前沿不是生成的新闻。</b><p>选择主题后，页面将直接展示学术目录中真实论文及其摘要；原始记录未提供摘要时会明确标注。</p></div>}
        <div className="frontierFeed">{result?.results.map((article, index) => <article className="frontierArticle" key={article.openalex_url}>
          <div className="frontierArticleMeta"><span>研究论文 · {article.year ?? "年份未提供"}</span><span>#{String(index + 1).padStart(2, "0")}</span></div>
          <h3>{article.title}</h3>
          <p className="frontierByline">{article.authors.slice(0, 5).join(" · ") || "作者未提供"}</p>
          <p className="frontierAbstract">{article.abstract ? `${article.abstract.slice(0, 560)}${article.abstract.length > 560 ? "…" : ""}` : "该论文的 OpenAlex 记录没有提供摘要。"}</p>
          <div className="frontierArticleLinks">{article.doi && <a href={article.doi} target="_blank" rel="noreferrer">DOI ↗</a>}<a href={article.openalex_url} target="_blank" rel="noreferrer">原始记录 ↗</a></div>
        </article>)}</div>
        {result && !result.results.length && <div className="libraryEmpty"><b>暂未找到相关文献</b><p>试试更宽泛的主题词。</p></div>}
        <footer className="frontierFooter">文献数据由 OpenAlex 提供 · 摘要及发表年份以来源记录为准</footer>
      </section>
      <aside className="frontierSidebar"><div><span>EXPLORE</span><h2>探索路径</h2>{topics.slice(0, 4).map((topic) => <button key={topic} onClick={() => { setQuery(topic); void explore(topic); }}>{topic}<span>↗</span></button>)}</div><div className="frontierSidebarNote"><b>研究者的阅读台</b><p>发现感兴趣的研究？前往文献库收藏记录并导出 CSV。</p><Link href="/library">打开我的文献库 →</Link></div></aside>
    </div>
  </main>;
}
