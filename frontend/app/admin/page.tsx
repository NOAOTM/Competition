"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";

type AdminUser = { id: number; username: string; phone?: string; nickname: string; grade: string; major: string; balance: number; quota: number; auth_status: string; is_active: boolean; created_at: string };

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try { setUsers(await api<AdminUser[]>("/api/v1/admin/users")); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "管理员用户列表加载失败"); }
  }
  useEffect(() => { void load(); }, []);

  async function update(user: AdminUser, values: { is_active?: boolean; balance?: number }) {
    setBusy(true);
    try { await api(`/api/v1/admin/users/${user.id}`, { method: "PATCH", body: JSON.stringify(values) }); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "用户修改失败"); }
    finally { setBusy(false); }
  }

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <h1>管理控制台</h1>
    <p>该页面由独立管理员账户保护；在本机 .env 配置 ADMIN_USERNAME 与 ADMIN_PASSWORD 后重启。</p>
    <section className="subPageCard">
      <div className="adminToolbar"><b>用户管理 · {users.length} 条</b><button onClick={load} disabled={busy}>刷新</button></div>
      {error && <p className="inlineError" role="alert">{error}</p>}
      {users.length > 0 && <div className="tableScroll"><table><thead><tr><th>账户</th><th>身份</th><th>额度余额</th><th>状态</th><th>操作</th></tr></thead><tbody>
        {users.map((user) => <tr key={user.id}><td>{user.nickname}<small>{user.phone || user.username}</small></td><td>{user.auth_status}</td><td><input aria-label={`${user.nickname}额度`} type="number" min="0" defaultValue={user.balance} onBlur={(event) => { const balance = Number(event.target.value); if (balance !== user.balance) void update(user, { balance }); }} /></td><td>{user.is_active ? "启用" : "停用"}</td><td><button disabled={busy} onClick={() => update(user, { is_active: !user.is_active })}>{user.is_active ? "停用" : "启用"}</button></td></tr>)}
      </tbody></table></div>}
      {!users.length && !error && <p>当前没有用户记录。</p>}
    </section>
  </main>;
}
