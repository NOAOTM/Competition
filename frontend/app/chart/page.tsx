"use client";

import Link from "next/link";
import { ChangeEvent, useState } from "react";

export default function ChartPage() {
  const [file, setFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [x, setX] = useState("");
  const [y, setY] = useState("");
  const [z, setZ] = useState("");
  const [type, setType] = useState("line");
  const [image, setImage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setError("");
    setImage("");
    const data = new FormData();
    data.set("file", selected);
    try {
      const response = await fetch("/api/v1/chart/columns", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` },
        body: data,
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "表格读取失败");
      setColumns(body.columns);
      setX(body.columns[0] ?? "");
      setY(body.columns[1] ?? body.columns[0] ?? "");
      setZ(body.columns[2] ?? "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "表格读取失败");
    }
  }

  async function render() {
    if (!file) return;
    setBusy(true);
    setError("");
    const data = new FormData();
    data.set("file", file);
    data.set("chart_type", type);
    data.set("x_column", x);
    data.set("y_column", y);
    data.set("z_column", z);
    try {
      const response = await fetch("/api/v1/chart/render", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` },
        body: data,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `图表生成失败（HTTP ${response.status}）`);
      }
      if (image) URL.revokeObjectURL(image);
      setImage(URL.createObjectURL(await response.blob()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "图表生成失败");
    } finally {
      setBusy(false);
    }
  }

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <h1>科研数据图表</h1>
    <p>上传 CSV 或 XLSX，选择字段生成 PNG。扫描表格 OCR 与清洗请先在本地整理为 CSV/XLSX。</p>
    <section className="subPageCard">
      <label>数据文件 <input type="file" accept=".csv,.xlsx" onChange={upload} /></label>
      {file && <p>已读取：{file.name}（{columns.length} 列）</p>}
      {columns.length > 0 && <div className="chartFields">
        <label>图表类型 <select value={type} onChange={(event) => setType(event.target.value)}><option value="line">折线图</option><option value="bar">柱状图</option><option value="pie">饼图</option><option value="scatter">散点图</option><option value="3d">3D 散点图</option></select></label>
        <label>X 轴/分类 <select value={x} onChange={(event) => setX(event.target.value)}>{columns.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>Y 轴/数值 <select value={y} onChange={(event) => setY(event.target.value)}>{columns.map((item) => <option key={item}>{item}</option>)}</select></label>
        {type === "3d" && <label>Z 轴 <select value={z} onChange={(event) => setZ(event.target.value)}>{columns.map((item) => <option key={item}>{item}</option>)}</select></label>}
        <button disabled={busy} onClick={render}>{busy ? "正在生成…" : "生成图表 PNG"}</button>
      </div>}
      {error && <p className="inlineError" role="alert">{error}</p>}
      {image && <div className="chartPreview"><img src={image} alt="生成的科研数据图表" /><a href={image} download="科研图表.png">下载 PNG</a></div>}
    </section>
  </main>;
}
