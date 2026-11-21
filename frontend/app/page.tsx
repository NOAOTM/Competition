"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChangeEvent, DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { ResearchTask, useResearchTasks } from "../components/research-task-provider";

type Health = {
  provider: string;
  model: string;
  reachable: boolean;
  mode: string;
  models: string[];
  model_available?: boolean;
  hint: string;
};

type UserInfo = { nickname: string; balance: number };

const nav = [
  { label: "科研助手", href: "/", icon: "✦", active: true },
  { label: "我的PS", href: "/ps", icon: "▧" },
  { label: "我的日程", href: "/schedule", icon: "▦" },
  { label: "我的账户", href: "/account", icon: "◉" },
];
const tools = [
  { label: "科研绘图", href: "/chart" },
  { label: "论文翻译", href: "/?feature=translate", feature: "translate" },
  { label: "研究设计", href: "/?feature=research-design", feature: "research-design" },
  { label: "文献导读", href: "/?feature=literature-guide", feature: "literature-guide" },
  { label: "文献库", href: "/library" },
  { label: "知识前沿", href: "/frontier" },
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
const recommendations = [
  { feature: "research-design", prompt: "请围绕我的研究主题，规划研究问题、研究设计、样本、方法、分析流程和潜在局限：", title: "开始一个新任务", description: "描述目标，生成可执行的研究方案" },
  { feature: "literature-guide", prompt: "请按研究背景、问题、方法、结果、结论和局限梳理这篇文献：", title: "导读一篇文献", description: "上传 PDF、Word 或纯文本后开始分析" },
  { feature: "polish", prompt: "请对以下学术内容进行语言润色，并列出主要修改理由：", title: "润色学术段落", description: "保留原意，改善表达与逻辑衔接" },
  { feature: "writing", prompt: "请根据以下主题生成论文写作提纲，并说明各部分要点：", title: "整理写作提纲", description: "从研究问题组织到章节结构" },
];

export default function Home() {
  const router = useRouter();
  const { tasks, submitting, startResearch, startTool } = useResearchTasks();
  const [feature, setFeature] = useState("literature-guide");
  const [selectedModel, setSelectedModel] = useState("");
  const [analysisMode, setAnalysisMode] = useState("standard");
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [recommendationsHidden, setRecommendationsHidden] = useState(false);
  const [recommendationOffset, setRecommendationOffset] = useState(0);
  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const [notice, setNotice] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("中文");
  const fileInput = useRef<HTMLInputElement>(null);
  const latestTask: ResearchTask | undefined = tasks[0];
  const activeFeature = featureChoices.find((item) => item.id === feature)?.label ?? "科研助手";

  useEffect(() => {
    const savedCollapsed = localStorage.getItem("sidebar-collapsed");
    if (savedCollapsed) setSidebarCollapsed(savedCollapsed === "true");
    const savedModel = localStorage.getItem("selected-model");
    const savedMode = localStorage.getItem("analysis-mode");
    const savedFeature = localStorage.getItem("selected-feature");
    if (savedModel) setSelectedModel(savedModel);
    if (savedMode && ["standard", "careful"].includes(savedMode)) setAnalysisMode(savedMode);
    if (savedFeature && featureChoices.some((item) => item.id === savedFeature)) setFeature(savedFeature);
    const refreshHealth = () => api<Health>("/api/v1/system/llm-health")
      .then((value) => {
        setHealth(value);
        setSelectedModel((current) => current || (value.models.includes(value.model) ? value.model : value.models[0] ?? value.model));
      })
      .catch(() => setHealth({ provider: "ollama", model: "deepseek-r1:7b", reachable: false, model_available: false, mode: "local", models: [], hint: "后端暂不可达，请运行 start.cmd 后重试" }));
    void refreshHealth();
    const healthTimer = window.setInterval(refreshHealth, 20_000);
    const readBalance = () => {
      if (!localStorage.getItem("token")) { setBalance(null); return; }
      void api<UserInfo>("/api/v1/account/me").then((user) => setBalance(user.balance)).catch(() => setBalance(null));
    };
    const updateBalance = (event: Event) => {
      const amount = (event as CustomEvent<number>).detail;
      if (Number.isFinite(amount)) setBalance(amount);
    };
    readBalance();
    window.addEventListener("storage", readBalance);
    window.addEventListener("zhenzhi:balance", updateBalance);
    const queryFeature = new URLSearchParams(window.location.search).get("feature");
    if (queryFeature && featureChoices.some((item) => item.id === queryFeature)) setFeature(queryFeature);
    setPreferencesLoaded(true);
    return () => {
      window.clearInterval(healthTimer);
      window.removeEventListener("storage", readBalance);
      window.removeEventListener("zhenzhi:balance", updateBalance);
    };
  }, []);

  useEffect(() => { if (preferencesLoaded && selectedModel) localStorage.setItem("selected-model", selectedModel); }, [preferencesLoaded, selectedModel]);
  useEffect(() => { if (preferencesLoaded) localStorage.setItem("analysis-mode", analysisMode); }, [preferencesLoaded, analysisMode]);
  useEffect(() => { if (preferencesLoaded) localStorage.setItem("selected-feature", feature); }, [preferencesLoaded, feature]);

  function toggleSidebar() {
    setSidebarCollapsed((current) => {
      localStorage.setItem("sidebar-collapsed", String(!current));
      return !current;
    });
  }

  function newTask() {
    setPrompt("");
    setFile(null);
    setNotice("");
    document.querySelector<HTMLTextAreaElement>(".composer textarea")?.focus();
  }

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
    if (!health) {
      setNotice("后端未连接，请检查 Docker 服务并运行 start.cmd");
      return;
    }
    if (!prompt.trim() && !file) {
      setNotice("请描述任务，或上传一份文献资料");
      return;
    }
    setNotice("");
    try {
      if (file) {
        const form = new FormData();
        form.set("file", file);
        form.set("question", prompt.trim() || "请导读这篇文献");
        form.set("model", selectedModel);
        form.set("analysis_mode", analysisMode);
        await startResearch(form, file.name);
        setFile(null);
        setPrompt("");
      } else {
        const requestPrompt = prompt;
        startTool({ feature, text: requestPrompt, target_language: targetLanguage, model: selectedModel, analysis_mode: analysisMode }, activeFeature);
        setPrompt("");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "任务失败，请查看服务状态后重试");
    }
  }

  const selectedModelAvailable = Boolean(health?.reachable && (health.models.includes(selectedModel || health.model) || health.model_available));
  const visibleRecommendations = recommendations.slice(recommendationOffset).concat(recommendations.slice(0, recommendationOffset)).slice(0, 3);
  const busy = submitting;

  return (
    <div className={`appShell${sidebarCollapsed ? " sidebarCollapsed" : ""}`}>
      <aside className="sidebar">
        <div className="brand"><span className="brandMark">✦</span><span><b>真知 Agent</b><small>研究与探索</small></span><button className="menuGlyph" onClick={toggleSidebar} aria-label="折叠或展开侧边栏">☰</button></div>
        <button className="newTask" onClick={newTask}>＋ 新建任务</button>
        <nav className="primaryNav">
          {nav.map((item) => <Link className={item.active ? "navItem selected" : "navItem"} href={item.href} key={item.label}><span>{item.icon}</span>{item.label}</Link>)}
        </nav>
        <div className="sideCaption">更多技能</div>
        <nav className="toolNav">{tools.map((item) => <Link className={item.feature === feature ? "selected" : ""} href={item.href} key={item.label} onClick={() => { if (item.feature) setFeature(item.feature); }}><span>✦</span>{item.label}</Link>)}</nav>
        <div className="sideFooter"><Link className="sidebarAccount" href="/account"><span className="sidebarAvatar">◉</span><span><b>{balance === null ? "我的账户" : `账户 · ${balance} 额度`}</b><small>{balance === null ? "登录 / 注册或查看额度" : "点击管理账户与认证"}</small></span><i>↗</i></Link><small className="localPrivacy">本地优先 · 你的资料留在自己的设备</small></div>
      </aside>

      <main className="mainArea">
        <header className="topBar">
          <div className="crumb">科研助手 <span>/</span> {activeFeature}{latestTask ? ` · ${latestTask.title}` : "新对话"}</div>
          <div className="topActions"><span className={health ? "onlineDot" : "offlineDot"} />{health ? (selectedModelAvailable ? "本地模型在线" : "工作台在线 · 模型未连接") : "后端未连接"}<Link className="quotaPill" href="/account">◇ 额度与账户</Link><Link className="accountAvatarLink" href="/account" title="打开我的账户" aria-label="打开我的账户">◉</Link></div>
        </header>
        <section className="workArea">
          <div className="welcomePill">✦ 真知 Agent · 配置驱动技能</div>
          <h1>准备开始你的任务了吗？</h1>
          {health && !selectedModelAvailable && <div className="healthBanner"><strong>{health.reachable ? "模型暂不可用" : "工作台未连接"}</strong><span>{health.hint} · 后端健康状态每 20 秒自动刷新</span></div>}

          <form className="composer cardSurface" onSubmit={submit} onDrop={handleDrop} onDragOver={(event) => event.preventDefault()}>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="描述你希望完成的任务……" disabled={busy} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(); } }} />
            {file && <div className="attachedFile"><span>▤</span>{file.name}<button type="button" onClick={() => setFile(null)} aria-label="移除文件">×</button></div>}
            <div className="composerToolbar">
              <button type="button" className="roundTool" aria-label="上传资料" onClick={() => fileInput.current?.click()}>↥</button>
              <input ref={fileInput} hidden type="file" accept=".pdf,.docx,.txt" onChange={handleFile} />
              <button type="button" className="roundTool" title="打开文献库" onClick={() => router.push("/library")}>▱</button>
              <select aria-label="选择功能" value={feature} onChange={(event) => setFeature(event.target.value)} disabled={busy}>
                {featureChoices.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
              <select aria-label="选择模型" title={selectedModel || health?.model || "deepseek-r1:7b"} value={selectedModel || health?.model || "deepseek-r1:7b"} onChange={(event) => setSelectedModel(event.target.value)} disabled={busy || !health?.models.length}>
                {(health?.models.length ? health.models : [health?.model || "deepseek-r1:7b"]).map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              {feature === "translate" && <select aria-label="目标语言" value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)}><option>中文</option><option>English</option><option>日本語</option><option>한국어</option></select>}
              <select aria-label="分析模式" value={analysisMode} onChange={(event) => setAnalysisMode(event.target.value)}><option value="standard">✦ 分析 · 标准</option><option value="careful">分析 · 详细核验</option></select>
              <button className="sendButton" type="submit" disabled={busy || !health} aria-label="开始任务">{busy ? <span className="spinner" /> : "↑"}</button>
            </div>
            {notice && <div className="inlineError" role="alert">{notice}</div>}
            {busy && <div className="taskProgress"><span className="spinner" /><div><b>正在提交任务</b><small>任务开始后会在切换页面时继续运行，并显示全局进度</small></div></div>}
          </form>

          {latestTask?.result && <section className="answerPanel cardSurface"><div className="answerHeader"><b>{latestTask.title} · 任务结果</b><button onClick={() => void navigator.clipboard.writeText(latestTask.result ?? "")}>复制</button></div><pre>{latestTask.result}</pre>{latestTask.downloads && <div className="downloadLinks">{latestTask.downloads.map((item) => <a href={item.url} key={item.url}>{item.label} ↓</a>)}</div>}</section>}

          <div className="recommendTitle"><span>为你推荐</span><span className="recommendControls"><button aria-label="换一组推荐" onClick={() => setRecommendationOffset((value) => (value + 1) % recommendations.length)}>⟳</button><button aria-label={recommendationsHidden ? "展开推荐" : "收起推荐"} onClick={() => setRecommendationsHidden((value) => !value)}>{recommendationsHidden ? "＋" : "×"}</button></span></div>
          {!recommendationsHidden && <div className="recommendGrid">{visibleRecommendations.map((item) => <button key={item.title} onClick={() => { setFeature(item.feature); setPrompt(item.prompt); document.querySelector<HTMLTextAreaElement>(".composer textarea")?.focus(); }}><i>✦</i><b>{item.title}</b><small>{item.description}</small><span className="cardArrow">↗</span></button>)}</div>}
          <p className="enterHint">Enter 发送 · Shift + Enter 换行</p>
        </section>
        <div className="quickActions"><button onClick={() => { setFeature("research-design"); document.querySelector("textarea")?.focus(); }}>✦ 开始任务</button><button onClick={() => fileInput.current?.click()}>▤ 上传资料</button><Link href="/library">⊙ 使用说明</Link></div>
      </main>
      <Link className="supportBubble" href="/account">♧ 在线帮助</Link>
    </div>
  );
}
