"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "../../lib/api";

type Place = { name: string; type: string; distance_km: number; price?: string | null; address: string; open_hours: string; map_url: string };
type FoodResult = { location: string; meal: string; results: Place[]; notice: string };

export default function FoodPage() {
  const [location, setLocation] = useState("");
  const [meal, setMeal] = useState("不限");
  const [sortBy, setSortBy] = useState<"distance" | "name">("distance");
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

  const places = [...(result?.results ?? [])].sort((a, b) => sortBy === "distance"
    ? a.distance_km - b.distance_km
    : a.name.localeCompare(b.name, "zh-CN"));

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <div className="foodHero">
      <div className="foodHeroCopy"><span className="foodEyebrow">CAMPUS FOOD · 附近觅食</span><h1>今天，想吃点什么？</h1><p>按位置发现真实餐饮地点，距离和已知价位一目了然。</p></div>
      <div className="foodHeroMark" aria-hidden="true">食</div>
      <form className="foodSearch" onSubmit={search}>
        <label><span>⌖</span><input required minLength={2} value={location} onChange={(event) => setLocation(event.target.value)} placeholder="输入学校、街道或城市" aria-label="定位" /></label>
        <label><span>◷</span><select value={meal} onChange={(event) => setMeal(event.target.value)} aria-label="餐型"><option>不限</option><option>早餐</option><option>午餐</option><option>晚餐</option><option>小吃</option></select></label>
        <button disabled={busy}>{busy ? "正在查找…" : "发现附近美食　→"}</button>
      </form>
    </div>
    <section className="foodDiscovery">
      <div className="foodSectionHeading"><div><span>附近的选择</span><h2>{result ? `在「${result.location}」发现` : "从你所在的位置开始"}</h2></div>
        {result && <label className="foodSort">排序 <select value={sortBy} onChange={(event) => setSortBy(event.target.value as "distance" | "name")}><option value="distance">距离最近</option><option value="name">名称顺序</option></select></label>}
      </div>
      {error && <p className="inlineError" role="alert">{error}</p>}
      {!result && !busy && <div className="foodEmpty"><span>⌖</span><b>搜索校区、街道或城市</b><p>我们会从 OpenStreetMap 获取附近餐饮地点，不展示虚构评分或照片。</p></div>}
      {busy && <div className="foodEmpty" role="status"><span>◌</span><b>正在查询真实地图数据</b><p>地址解析与附近地点检索可能需要一点时间。</p></div>}
      {result && <><p className="dataNotice">{result.notice}</p><div className="foodGrid">{places.map((place, index) =>
        <article className="foodCard" key={`${place.name}-${index}`}>
          <div className={`foodCardIllustration foodIllustration${index % 4}`} aria-hidden="true"><span>{place.type.toLowerCase().includes("cafe") ? "☕" : place.type.toLowerCase().includes("fast") ? "🍜" : "餐"}</span><small>地图地点</small></div>
          <div className="foodCardBody"><div className="foodCardMeta"><span>{place.type || "餐饮地点"}</span><b>{place.distance_km} km</b></div>
            <h3>{place.name}</h3><p className="foodPrice">{place.price ?? "价位暂无可靠数据"}</p>
            <p className="foodAddress">{place.address || "地址信息未提供"}</p>
            {place.open_hours && <p className="foodHours">营业时间标签：{place.open_hours}</p>}
            <a href={place.map_url} target="_blank" rel="noreferrer">在地图中查看 <span>↗</span></a>
          </div>
        </article>)}</div>
        {!places.length && <div className="foodEmpty"><span>⌕</span><b>没有找到餐饮地点</b><p>地图数据没有匹配项，请换一个更具体的位置再试。</p></div>}
      </>}
    </section>
  </main>;
}
