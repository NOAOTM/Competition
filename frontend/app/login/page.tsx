"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await api<{ access_token: string }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
      localStorage.setItem("token", result.access_token);
      setMessage("登录成功");
      router.push("/");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "登录失败");
    }
  }
  return <main className="loginPage"><div className="loginCard"><Link className="backLink" href="/">← 返回科研助手</Link><h1>登录真知 Agent</h1><form onSubmit={submit}><p><input aria-label="手机号 / 用户名" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="手机号 / 用户名" /></p><p><input aria-label="密码" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="密码" /></p><button type="submit">登录</button></form><p>{message}</p><Link href="/account">还没有账户？手机号注册</Link></div></main>;
}
