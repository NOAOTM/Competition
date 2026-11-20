"use client";

import Link from "next/link";
import { ChangeEvent, DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

type Health = {
  provider: string;
  model: string;
  reachable: boolean;
  mode: string;
  models: string[];
  model_available?: boolean;
  hint: string;
};

type ToolResult = { result: string; cost: number; balance: number };
type ResearchProgress = {
  status: "queued" | "running" | "done" | "error";
  progress: number;
  stage: string;
  message: string;
  result?: { summary?: string; downloads?: { label: string; url: string }[] };
  error?: string;
};

const nav = [
  { label: "科研助手", href: "/", icon: "✦", active: true },
  { label: "创作伙伴", href: "/ps", icon: "▧" },
  { label: "我的日程", href: "/schedule", icon: "▦" },
  { label: "我的账户", href: "/account", icon: "◉" },
];
const tools = [
  { label: "科研绘图", href: "/chart" },
  { label: "论文翻译", href: "/?feature=translate" },
  { label: "研究设计", href: "/?feature=research-design" },
  { label: "文献导读", href: "/?feature=literature-guide" },
  { label: "文献库", href: "/library" },
  { label: "知识前沿", href: "/?feature=knowledge-frontier" },
  { label: "数据分析", href: "/chart" },
  { label: "美食推荐", href: "/food" },
];
const featureChoices = [
  { id: "literature-guide", label: "文献导读" },
  { id: "research-design", label: "研究设计" },
  { id: "polish", label: "学术润色" },
  { id: "translate", label: "论文翻译" },
  { id: "knowledge-frontier", label: "知识前沿" },
  { id: "diagram", label: "逻辑图" },
  { id: "data-analysis", label: "数据分析" },
  { id: "literature-search", label: "文献检索策略" },
  { id: "writing", label: "写作提纲" },
  { id: "study-plan", label: "学习计划" },
];

export default function Home() {
  const [feature, setFeature] = useState("literature-guide");
  const [selectedModel, setSelectedModel] = useState("");
  const [analysisMode, setAnalysisMode] = useState("standard");
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<ResearchProgress | null>(null);
  const [answer, setAnswer] = useState("");
  const [notice, setNotice] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("中文");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api<Health>("/api/v1/system/llm-health")
      .then((value) => { setHealth(value); setSelectedModel(value.models.includes(value.model) ? value.model : value.models[0] ?? value.model); })
      .catch(() => setHealth({ provider: "ollama", model: "deepseek-r1:7b", reachable: false, model_available: false, mode: "local", models: [], hint: "后端暂不可达，请运行 start.cmd 后重试" }));
    const queryFeature = new URLSearchParams(window.location.search).get("feature");
    if (queryFeature && featureChoices.some((item) => item.id === queryFeature)) setFeature(queryFeature);
  }, []);

  function chooseFile(next: File | undefined) {
    if (!next) return;
    if (!/\.(pdf|docx|txt)$/i.test(next.name)) {
      setNotice("目前支持 PDF、DOCX 和纯文本文件");
      return;
    }
    setNotice("");
    setFile(next);
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLFormElement>) {
    event.preventDefault();
    chooseFile(event.dataTransfer.files?.[0]);
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!prompt.trim() && !file) {
      setNotice("请描述任务，或上传一份文献资料");
      return;
    }
    setBusy(true);
    setNotice("");
    setAnswer("");
    setProgress(null);
    try {
      if (file) {
        const token = localStorage.getItem("token");
        if (!token) throw new Error("请先登录后再提交文献任务");
        const form = new FormData();
        form.set("file", file);
        form.set("question", prompt.trim() || "请导读这篇文献");
        form.set("model", selectedModel);
        form.set("analysis_mode", analysisMode);
        const response = await fetch("/api/v1/agent/research", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        });
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(body?.detail ?? `提交失败（HTTP ${response.status}）`);
        const startedAt = Date.now();
        let completed = false;
        while (Date.now() - startedAt < 360_000) {
          await new Promise((resolve) => setTimeout(resolve, 2200));
          const current = await api<ResearchProgress>(`/api/v1/agent/progress/${body.task_id}`);
          setProgress(current);
          if (current.status === "done") {
            setAnswer(current.result?.summary ?? "任务已完成，请下载生成的报告文件。");
            completed = true;
            break;
          }
          if (current.status === "error") throw new Error(current.error || "文献处理失败");
        }
        if (!completed) {
          throw new Error("任务等待超过 6 分钟；可在任务进度中查看，未成功的生成不会记作完成");
        }
      } else {
        const result = await api<ToolResult>("/api/v1/tools/run", {
          method: "POST",
          body: JSON.stringify({ feature, text: prompt, target_language: targetLanguage, model: selectedModel, analysis_mode: analysisMode }),
        });
        setAnswer(result.result);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "任务失败，请查看服务状态后重试");
    } finally {
      setBusy(false);
    }
  }

  const selectedModelAvailable = Boolean(
    health?.reachable && (health.models.includes(selectedModel || health.model) || health.model_available),
  );

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand"><span className="brandMark">✦</span><span><b>真知 Agent</b><small>研究与探索</small></span><span className="menuGlyph">☰</span></div>
        <button className="newTask" onClick={() => { setPrompt(""); setAnswer(""); setFile(null); }}>＋ 新建任务</button>
        <nav className="primaryNav">
          {nav.map((item) => <Link className={item.active ? "navItem selected" : "navItem"} href={item.href} key={item.label}><span>{item.icon}</span>{item.label}</Link>)}
        </nav>
        <div className="sideCaption">更多技能</div>
        <nav className="toolNav">{tools.map((item) => <Link href={item.href} key={item.label}><span>✦</span>{item.label}</Link>)}</nav>
        <div className="sideFooter">本地优先 · 你的资料留在自己的设备</div>
      </aside>

      <main className="mainArea">
        <header className="topBar">
          <div className="crumb">科研助手 <span>/</span> 新对话</div>
          <div className="topActions"><Link href="/login">登录 / 注册</Link><span className={selectedModelAvailable ? "onlineDot" : "offlineDot"} />{selectedModelAvailable ? "本地模型在线" : "模型未连接"}<Link className="quotaPill" href="/account">◇ 额度与账户</Link></div>
        </header>
        <section className="workArea">
          <div className="welcomePill">✦ 真知 Agent · 配置驱动技能</div>
          <h1>准备开始你的任务了吗？</h1>
          {health && !selectedModelAvailable && <div className="healthBanner"><strong>模型暂不可用</strong><span>{health.hint} · 在服务启动后可刷新页面重试</span></div>}

          <form className="composer cardSurface" onSubmit={submit} onDrop={handleDrop} onDragOver={(event) => event.preventDefault()}>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="描述你希望完成的任务……" disabled={busy} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(); } }} />
            {file && <div className="attachedFile"><span>▤</span>{file.name}<button type="button" onClick={() => setFile(null)} aria-label="移除文件">×</button></div>}
            <div className="composerToolbar">
              <button type="button" className="roundTool" aria-label="上传资料" onClick={() => fileInput.current?.click()}>↥</button>
              <input ref={fileInput} hidden type="file" accept=".pdf,.docx,.txt" onChange={handleFile} />
              <button type="button" className="roundTool" title="支持 PDF、DOCX、TXT" onClick={() => fileInput.current?.click()}>▱</button>
              <select aria-label="选择功能" value={feature} onChange={(event) => setFeature(event.target.value)} disabled={busy}>
                {featureChoices.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
              <select aria-label="选择模型" value={selectedModel || health?.model || "deepseek-r1:7b"} onChange={(event) => setSelectedModel(event.target.value)} disabled={busy || !health?.models.length}>
                {(health?.models.length ? health.models : [health?.model || "deepseek-r1:7b"]).map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              {feature === "translate" && <select aria-label="目标语言" value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)}><option>中文</option><option>English</option><option>日本語</option><option>한국어</option></select>}
              <select aria-label="分析模式" value={analysisMode} onChange={(event) => setAnalysisMode(event.target.value)}><option value="standard">✦ 分析 · 标准</option><option value="careful">分析 · 详细核验</option></select>
              <button className="sendButton" type="submit" disabled={busy} aria-label="开始任务">{busy ? <span className="spinner" /> : "↑"}</button>
            </div>
            {notice && <div className="inlineError" role="alert">{notice}</div>}
            {busy && <div className="taskProgress"><div className="progressTrack"><span style={{ width: `${Math.max(8, progress?.progress ?? 12)}%` }} /></div><div><b>{progress?.stage || "正在连接本地模型并生成内容"}</b><small>{progress?.message || "长任务最多等待 6 分钟，期间不会返回示例结果"}</small></div></div>}
          </form>

          {answer && <section className="answerPanel cardSurface"><div className="answerHeader"><b>任务结果</b><button onClick={() => navigator.clipboard.writeText(answer)}>复制</button></div><pre>{answer}</pre>{progress?.result?.downloads && <div className="downloadLinks">{progress.result.downloads.map((item) => <a href={item.url} key={item.url}>{item.label} ↓</a>)}</div>}</section>}

          <div className="recommendTitle"><span>为你推荐</span><span>⟳　×</span></div>
          <div className="recommendGrid">
            <button onClick={() => { setFeature("research-design"); setPrompt("请帮我规划一项研究："); }}><i>✦</i><b>开始一个新任务</b><small>先描述目标，连接真实本地模型完成分析</small><span className="cardArrow">↗</span></button>
            <button onClick={() => fileInput.current?.click()}><i>▤</i><b>上传资料开始分析</b><small>支持 PDF、Word 和纯文本，后台展示处理进度</small><span className="cardArrow">↗</span></button>
            <Link href="/library"><i>◎</i><b>查看使用说明</b><small>模型、隐私与功能边界都在这里说明</small><span className="cardArrow">↗</span></Link>
          </div>
          <p className="enterHint">Enter 发送 · Shift + Enter 换行</p>
        </section>
        <div className="quickActions"><button onClick={() => { setFeature("research-design"); document.querySelector("textarea")?.focus(); }}>✦ 开始任务</button><button onClick={() => fileInput.current?.click()}>▤ 上传资料</button><Link href="/library">⊙ 使用说明</Link></div>
      </main>
      <Link className="supportBubble" href="/account">♧ 在线帮助</Link>
    </div>
  );
}
