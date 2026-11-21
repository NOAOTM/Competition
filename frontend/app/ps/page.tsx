"use client";

import Link from "next/link";
import { useRef, useState } from "react";

export default function PhotoCraftPage() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [reloadKey, setReloadKey] = useState(0);

  async function toggleFullscreen() {
    const target = frame.current;
    if (!target) return;
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    await target.requestFullscreen();
  }

  return <main className="photoCraftPage">
    <header className="photoCraftHeader">
      <Link href="/" className="photoCraftBack">← 科研助手</Link>
      <div><strong>我的 PS</strong><span>PhotoCraft · 专业图像创作工作台</span></div>
      <div className="photoCraftActions">
        <span className="photoCraftStatus">本地浏览器编辑 · 文件保存在你的设备</span>
        <button type="button" onClick={() => setReloadKey((key) => key + 1)}>重新载入</button>
        <button type="button" onClick={() => void toggleFullscreen()}>全屏工作</button>
      </div>
    </header>
    <div className="photoCraftNotice">
      <span>ⓘ</span> 编辑器由 PhotoCraft 提供，图像在浏览器中处理，不会上传到真知 Agent。建议使用支持 WebGPU 或 WebGL2 的现代浏览器。
      <details><summary>开源许可</summary><p>PhotoCraft Web 发布包附带 MIT 许可、NOTICE 与素材归属说明，可查看 <a href="/photocraft/licenses/LICENSE-MIT" target="_blank" rel="noreferrer">MIT 许可</a>。</p></details>
    </div>
    <iframe
      key={reloadKey}
      ref={frame}
      className="photoCraftFrame"
      src="/photocraft/index.html"
      title="PhotoCraft 图像编辑工作台"
      allow="fullscreen; clipboard-read; clipboard-write"
      allowFullScreen
    />
  </main>;
}
