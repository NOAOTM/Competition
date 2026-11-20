"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";

type CalendarItem = { id: number; title: string; starts_at: string; ends_at?: string | null; kind: string; details: string; source: string };
const dayLabels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

function localDate(value: Date) {
  const copy = new Date(value);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

export default function SchedulePage() {
  const [items, setItems] = useState<CalendarItem[]>([]);
  const [title, setTitle] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [details, setDetails] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const week = useMemo(() => {
    const today = localDate(new Date());
    const monday = new Date(today);
    monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
    return dayLabels.map((label, index) => {
      const date = new Date(monday);
      date.setDate(monday.getDate() + index);
      return { label, date };
    });
  }, []);

  async function refresh() {
    try { setItems(await api<CalendarItem[]>("/api/v1/schedule/items")); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "日历加载失败"); }
  }
  useEffect(() => { void refresh(); }, []);

  async function addReminder(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/schedule/reminders", { method: "POST", body: JSON.stringify({ title, starts_at: new Date(startsAt).toISOString(), details }) });
      setTitle(""); setDetails(""); setStartsAt(""); setNotice("提醒已保存"); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "提醒保存失败"); }
  }

  async function importSchedule(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const data = new FormData(); data.set("file", file);
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/api/v1/schedule/import", { method: "POST", headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` }, body: data });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "导入失败");
      setNotice(body.message); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "课表导入失败"); }
    finally { setBusy(false); event.target.value = ""; }
  }

  async function syncChaoxing() {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await api<{ message: string; deadlines_found: number }>("/api/v1/schedule/chaoxing/sync", { method: "POST" });
      setNotice(`${result.message}（找到 ${result.deadlines_found} 个日期）`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "学习通同步失败"); }
    finally { setBusy(false); }
  }

  async function remove(id: number) {
    try { await api(`/api/v1/schedule/items/${id}`, { method: "DELETE" }); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "删除日程失败"); }
  }

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <h1>我的日程</h1>
    <p>导入 CSV/XLSX 课表，维护课程与提醒；周历以本机当前日期显示。</p>
    <section className="subPageCard">
      <div className="scheduleActions"><label className="uploadButton">导入 CSV/XLSX<input type="file" accept=".csv,.xlsx" onChange={importSchedule} disabled={busy} /></label><button onClick={syncChaoxing} disabled={busy}>同步学习通作业</button><a href="https://i.mooc.chaoxing.com/" target="_blank" rel="noreferrer">打开学习通 ↗</a></div>
      <div className="weekGrid">{week.map((day) => {
        const key = day.date.toDateString();
        const dayItems = items.filter((item) => new Date(item.starts_at).toDateString() === key);
        return <section className="dayColumn" key={key}><b>{day.label}</b><small>{day.date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" })}</small>
          {dayItems.map((item) => <article className={item.kind === "class" ? "calendarItem classItem" : "calendarItem"} key={item.id}>
            <strong>{new Date(item.starts_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</strong><span>{item.title}</span>{item.details && <small>{item.details}</small>}<button onClick={() => remove(item.id)} aria-label={`删除${item.title}`}>×</button>
          </article>)}
        </section>;
      })}</div>
      <h2>添加提醒</h2>
      <form className="reminderForm" onSubmit={addReminder}>
        <input required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="提醒标题" />
        <input required type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} />
        <input value={details} onChange={(event) => setDetails(event.target.value)} placeholder="备注（可选）" />
        <button>保存提醒</button>
      </form>
      {notice && <p className="successNotice">{notice}</p>}
      {error && <p className="inlineError" role="alert">{error}</p>}
    </section>
  </main>;
}
