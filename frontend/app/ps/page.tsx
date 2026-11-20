"use client";

import Link from "next/link";
import { ChangeEvent, PointerEvent, useEffect, useRef, useState } from "react";

type Tool = "move" | "brush" | "eraser" | "line" | "rect" | "text";
type Layer = { id: string; name: string; visible: boolean; opacity: number };
type HistoryItem = { layerId: string; image: string; label: string };
const WIDTH = 1000;
const HEIGHT = 650;
const toolOptions: { id: Tool; icon: string; label: string }[] = [
  { id: "move", icon: "✥", label: "移动" },
  { id: "brush", icon: "╱", label: "画笔" },
  { id: "eraser", icon: "◩", label: "橡皮擦" },
  { id: "line", icon: "／", label: "直线" },
  { id: "rect", icon: "□", label: "矩形" },
  { id: "text", icon: "T", label: "文字" },
];

export default function PhotoshopWorkspace() {
  const [tool, setTool] = useState<Tool>("brush");
  const [color, setColor] = useState("#252525");
  const [brushSize, setBrushSize] = useState(8);
  const [text, setText] = useState("双击画布添加文字");
  const [layers, setLayers] = useState<Layer[]>([{ id: "layer-1", name: "背景", visible: true, opacity: 1 }]);
  const [activeLayer, setActiveLayer] = useState("layer-1");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [notice, setNotice] = useState("");
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const layerRefs = useRef<Record<string, HTMLCanvasElement | null>>({});
  const fileRef = useRef<HTMLInputElement>(null);
  const drawing = useRef(false);
  const start = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = layerRefs.current["layer-1"];
    const ctx = canvas?.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, WIDTH, HEIGHT);
      saveHistory("创建画布", "layer-1");
    }
  }, []);

  function getPoint(event: PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * WIDTH / rect.width,
      y: (event.clientY - rect.top) * HEIGHT / rect.height,
    };
  }

  function saveHistory(label: string, layerId = activeLayer) {
    const canvas = layerRefs.current[layerId];
    if (!canvas) return;
    const image = canvas.toDataURL("image/png");
    const next = history.slice(0, historyIndex + 1);
    next.push({ layerId, image, label });
    const limited = next.slice(-30);
    setHistory(limited);
    setHistoryIndex(limited.length - 1);
  }

  function onPointerDown(event: PointerEvent<HTMLCanvasElement>) {
    if (tool === "move") return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const point = getPoint(event);
    start.current = point;
    drawing.current = true;
    const canvas = layerRefs.current[activeLayer];
    const ctx = canvas?.getContext("2d");
    if (!ctx) return;
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
    if (tool === "text") {
      ctx.fillStyle = color;
      ctx.font = "32px 'Microsoft YaHei', sans-serif";
      ctx.fillText(text || "文字", point.x, point.y);
      drawing.current = false;
      saveHistory("添加文字");
    }
  }

  function onPointerMove(event: PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) return;
    const point = getPoint(event);
    const ctx = layerRefs.current[activeLayer]?.getContext("2d");
    if (!ctx) return;
    ctx.lineWidth = brushSize;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = color;
    if (tool === "eraser") {
      ctx.globalCompositeOperation = "destination-out";
      ctx.lineTo(point.x, point.y);
      ctx.stroke();
      ctx.globalCompositeOperation = "source-over";
    } else if (tool === "brush") {
      ctx.lineTo(point.x, point.y);
      ctx.stroke();
    }
  }

  function onPointerUp(event: PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) return;
    const point = getPoint(event);
    const ctx = layerRefs.current[activeLayer]?.getContext("2d");
    if (ctx && (tool === "line" || tool === "rect")) {
      ctx.strokeStyle = color;
      ctx.lineWidth = brushSize;
      ctx.beginPath();
      if (tool === "line") {
        ctx.moveTo(start.current.x, start.current.y);
        ctx.lineTo(point.x, point.y);
      } else {
        ctx.rect(start.current.x, start.current.y, point.x - start.current.x, point.y - start.current.y);
      }
      ctx.stroke();
    }
    drawing.current = false;
    saveHistory(toolOptions.find((item) => item.id === tool)?.label ?? "编辑");
  }

  function addLayer() {
    const id = `layer-${Date.now()}`;
    setLayers((value) => [...value, { id, name: `图层 ${value.length}`, visible: true, opacity: 1 }]);
    setActiveLayer(id);
    setNotice("已新建透明图层");
  }

  function toggleLayer(id: string) {
    setLayers((value) => value.map((layer) => layer.id === id ? { ...layer, visible: !layer.visible } : layer));
  }

  function deleteLayer(id: string) {
    if (layers.length <= 1) {
      setNotice("至少保留一个图层");
      return;
    }
    const remaining = layers.filter((layer) => layer.id !== id);
    setLayers(remaining);
    if (activeLayer === id) setActiveLayer(remaining[remaining.length - 1].id);
    delete layerRefs.current[id];
  }

  function loadImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setNotice("请选择 PNG、JPEG、WebP 等图片文件");
      return;
    }
    const image = new Image();
    image.onload = () => {
      const ctx = layerRefs.current[activeLayer]?.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, WIDTH, HEIGHT);
      const ratio = Math.min(WIDTH / image.width, HEIGHT / image.height);
      const width = image.width * ratio;
      const height = image.height * ratio;
      ctx.drawImage(image, (WIDTH - width) / 2, (HEIGHT - height) / 2, width, height);
      saveHistory(`导入 ${file.name}`);
      setNotice(`已将 ${file.name} 导入当前图层`);
      URL.revokeObjectURL(image.src);
    };
    image.onerror = () => setNotice("图片无法读取，请确认文件格式有效");
    image.src = URL.createObjectURL(file);
    event.target.value = "";
  }

  function restoreHistory(index: number) {
    const item = history[index];
    const canvas = item && layerRefs.current[item.layerId];
    const ctx = canvas?.getContext("2d");
    if (!item || !canvas || !ctx) return;
    const image = new Image();
    image.onload = () => {
      ctx.clearRect(0, 0, WIDTH, HEIGHT);
      ctx.drawImage(image, 0, 0);
      setActiveLayer(item.layerId);
      setHistoryIndex(index);
    };
    image.src = item.image;
  }

  function exportPng() {
    const output = document.createElement("canvas");
    output.width = WIDTH;
    output.height = HEIGHT;
    const ctx = output.getContext("2d");
    if (!ctx) {
      setNotice("无法创建导出画布");
      return;
    }
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.filter = `brightness(${brightness}%) contrast(${contrast}%)`;
    layers.filter((layer) => layer.visible).forEach((layer) => {
      const canvas = layerRefs.current[layer.id];
      if (!canvas) return;
      ctx.globalAlpha = layer.opacity;
      ctx.drawImage(canvas, 0, 0);
    });
    ctx.globalAlpha = 1;
    ctx.filter = "none";
    const link = document.createElement("a");
    link.download = "真知创作.png";
    link.href = output.toDataURL("image/png");
    link.click();
    setNotice("PNG 已导出到下载目录");
  }

  function undo() {
    if (historyIndex > 0) restoreHistory(historyIndex - 1);
  }

  function redo() {
    if (historyIndex < history.length - 1) restoreHistory(historyIndex + 1);
  }

  return (
    <main className="editorShell">
      <header className="editorMenu">
        <Link href="/" aria-label="返回科研助手">✦</Link><span>文件</span><span>编辑</span><span>图像</span><span>图层</span><span>文字</span><span>选择</span><span>滤镜</span><span>视图</span><span>窗口</span><span>帮助</span>
      </header>
      <header className="editorTop">
        <Link href="/" className="editorTitle">真知创作 · 未命名作品</Link>
        <button onClick={undo} disabled={historyIndex <= 0}>↶ 撤销</button><button onClick={redo} disabled={historyIndex >= history.length - 1}>↷ 重做</button>
        <span>画笔大小</span><input aria-label="画笔大小" type="range" min="1" max="60" value={brushSize} onChange={(event) => setBrushSize(Number(event.target.value))} />
        <button onClick={() => fileRef.current?.click()}>导入图片</button><button onClick={exportPng}>导出 PNG</button>
        <input ref={fileRef} hidden type="file" accept="image/*" onChange={loadImage} />
      </header>
      <div className="editorLayout">
        <aside className="editorTools" aria-label="编辑工具">
          {toolOptions.map((item) => <button key={item.id} className={tool === item.id ? "active" : ""} title={item.label} aria-label={item.label} onClick={() => setTool(item.id)}>{item.icon}</button>)}
          <button title="打开图片" onClick={() => fileRef.current?.click()}>▧</button>
        </aside>
        <section className="canvasWorkspace">
          <div className="canvasStage">
            {layers.map((layer) => <canvas key={layer.id} ref={(element) => { layerRefs.current[layer.id] = element; if (element && (element.width !== WIDTH || element.height !== HEIGHT)) { element.width = WIDTH; element.height = HEIGHT; } }} className="canvasFrame layerCanvas" width={WIDTH} height={HEIGHT} style={{ visibility: layer.visible ? "visible" : "hidden", opacity: layer.opacity, filter: `brightness(${brightness}%) contrast(${contrast}%)` }} />)}
            <canvas className="canvasFrame inputCanvas" width={WIDTH} height={HEIGHT} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp} />
          </div>
          <div className="canvasStatus"><span>真知创作.psd　·　{WIDTH} × {HEIGHT}px</span><span>缩放 100%</span></div>
          {notice && <div className="editorNotice" role="status">{notice}</div>}
        </section>
        <aside className="editorPanel">
          <div className="panelTabs"><b>图层</b><span>历史记录</span><span>颜色</span></div>
          <h3>工具属性 · {toolOptions.find((item) => item.id === tool)?.label}</h3>
          <div>前景色 <input aria-label="前景色" type="color" value={color} onChange={(event) => setColor(event.target.value)} />　大小 {brushSize}px</div>
          {tool === "text" && <p><input aria-label="文字内容" value={text} onChange={(event) => setText(event.target.value)} /></p>}
          <h3>调整</h3>
          <label className="adjustRow">亮度 {brightness}% <input type="range" min="25" max="175" value={brightness} onChange={(event) => setBrightness(Number(event.target.value))} /></label>
          <label className="adjustRow">对比度 {contrast}% <input type="range" min="25" max="175" value={contrast} onChange={(event) => setContrast(Number(event.target.value))} /></label>
          <h3>图层 <button onClick={addLayer}>＋ 新建</button></h3>
          {[...layers].reverse().map((layer) => <div key={layer.id} className={`layerRow ${activeLayer === layer.id ? "active" : ""}`} onClick={() => setActiveLayer(layer.id)}>
            <input type="checkbox" checked={layer.visible} onChange={() => toggleLayer(layer.id)} aria-label={`${layer.name} 可见`} />
            <span>{layer.name}</span>
            <input type="range" min="0" max="1" step="0.05" value={layer.opacity} aria-label={`${layer.name} 不透明度`} onChange={(event) => setLayers((items) => items.map((item) => item.id === layer.id ? { ...item, opacity: Number(event.target.value) } : item))} />
            <button onClick={(event) => { event.stopPropagation(); deleteLayer(layer.id); }}>×</button>
          </div>)}
          <h3>历史记录</h3>
          <div className="editorHistory">{history.map((item, index) => <button key={`${item.layerId}-${index}`} className={historyIndex === index ? "active" : ""} onClick={() => restoreHistory(index)}>{item.label}</button>)}</div>
          <p className="editorHint">画笔、橡皮擦、直线、矩形和文字均在本地画布中编辑；图层、撤销/重做、图片导入和 PNG 导出无需外部服务。</p>
        </aside>
      </div>
    </main>
  );
}
