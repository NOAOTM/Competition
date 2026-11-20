"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "../../lib/api";

type Place = { name: string; type: string; distance_km: number; price?: string | null; address: string; open_hours: string; map_url: string };
type FoodResult = { location: string; meal: string; results: Place[]; notice: string };

export default function FoodPage() {
  const [location, setLocation] = useState("");
  const [meal, setMeal] = useState("不限");
  const [result, setResult] = useState<FoodResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function search(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await api<FoodResult>(`/api/v1/food/search?location=${encodeURIComponent(location)}&meal=${encodeURIComponent(meal)}`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "附近餐馆检索失败");
    } finally {
      setBusy(false);
    }
  }

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <h1>美食推荐</h1>
    <p>输入地点，查找附近真实餐饮地点。结果由 OpenStreetMap 提供，按已知价位标签和距离排列，不使用虚构评分。</p>
    <section className="subPageCard">
      <form className="inlineForm" onSubmit={search}>
        <input required minLength={2} value={location} onChange={(event) => setLocation(event.target.value)} placeholder="校区、街道或城市" aria-label="定位" />
        <select value={meal} onChange={(event) => setMeal(event.target.value)} aria-label="餐型"><option>不限</option><option>早餐</option><option>午餐</option><option>晚餐</option><option>小吃</option></select>
        <button disabled={busy}>{busy ? "定位与检索中…" : "搜索附近餐馆"}</button>
      </form>
      {error && <p className="inlineError" role="alert">{error}</p>}
      {result && <><p>位置：{result.location} · 餐型：{result.meal}</p><p className="dataNotice">{result.notice}</p>
        {result.results.map((place, index) => <article className="foodResult" key={`${place.name}-${index}`}>
          <div><b>{place.name}</b><span>{place.type} · {place.distance_km} km</span></div>
          <p>价位：{place.price ?? "暂无可靠价位数据"}{place.address && ` · ${place.address}`}</p>
          {place.open_hours && <small>营业时间标签：{place.open_hours}</small>}
          <a href={place.map_url} target="_blank" rel="noreferrer">地图位置 ↗</a>
        </article>)}
        {!result.results.length && <p>当前地图数据未提供附近餐馆名称，请尝试更具体的位置。</p>}
      </>}
    </section>
  </main>;
}
