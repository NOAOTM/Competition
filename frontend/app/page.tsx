import Link from "next/link";

export default function Home() {
  return <main><nav><strong>🧠 真知 Agent</strong><Link href="/login">登录 / 注册</Link></nav><section className="card"><h1>把时间留给真正重要的学习</h1><p>文献导读、学术润色、翻译与学习效率工具，统一在一个可靠的助手中完成。</p><Link href="/login"><button>开始使用</button></Link></section></main>;
}
