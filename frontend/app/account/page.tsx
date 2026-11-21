"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { api } from "../../lib/api";

type Captcha = { captcha_id: string; question: string };
type UserInfo = { username: string; phone?: string; nickname: string; grade: string; major: string; balance: number; quota: number; auth_status: string; verification_status: string; is_admin: boolean };

export default function AccountPage() {
  const [captcha, setCaptcha] = useState<Captcha | null>(null);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [smsCode, setSmsCode] = useState("");
  const [demoCode, setDemoCode] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [grade, setGrade] = useState("本科");
  const [major, setMajor] = useState("");
  const [loginPhone, setLoginPhone] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [user, setUser] = useState<UserInfo | null>(null);
  const [studentName, setStudentName] = useState("");
  const [school, setSchool] = useState("");
  const [studentCard, setStudentCard] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [smsCooldown, setSmsCooldown] = useState(0);
  const expectedCaptchaAnswer = captcha?.question.match(/^\s*(\d+)\s*\+\s*(\d+)/);
  const captchaValid = Boolean(expectedCaptchaAnswer && captchaAnswer.trim() === String(Number(expectedCaptchaAnswer[1]) + Number(expectedCaptchaAnswer[2])));

  useEffect(() => {
    if (smsCooldown <= 0) return;
    const timer = window.setTimeout(() => setSmsCooldown((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [smsCooldown]);

  async function loadCaptcha() {
    try { setCaptcha(await api<Captcha>("/api/v1/account/captcha")); }
    catch { setCaptcha(null); }
  }
  async function loadUser() {
    try { setUser(await api<UserInfo>("/api/v1/account/me")); }
    catch { setUser(null); }
  }
  useEffect(() => { void loadCaptcha(); void loadUser(); }, []);

  async function sendSms() {
    setError(""); setNotice("");
    if (!/^1[3-9]\d{9}$/.test(phone)) { setError("请输入有效的 11 位手机号"); return; }
    if (!captchaValid || !captcha) { setError("请先正确完成算术验证码"); return; }
    try {
      const response = await fetch("/api/v1/account/sms-code", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, captcha_id: captcha?.captcha_id, captcha_answer: captchaAnswer }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "验证码发送失败");
      setDemoCode(body.code ?? "");
      setNotice(body.message);
      setSmsCooldown(60);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "验证码发送失败"); }
  }

  async function register(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/api/v1/account/register", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, sms_code: smsCode, password, nickname, grade, major }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "注册失败");
      const login = await fetch("/api/v1/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: phone, password }),
      });
      const token = await login.json();
      if (!login.ok) throw new Error(token.detail ?? "注册成功，但自动登录失败，请手动登录");
      localStorage.setItem("token", token.access_token);
      setNotice("注册成功，已登录");
      await loadUser();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "注册失败"); }
    finally { setBusy(false); }
  }

  async function login(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: loginPhone, password: loginPassword }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "登录失败");
      localStorage.setItem("token", body.access_token);
      setNotice("登录成功"); await loadUser();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "登录失败"); }
    finally { setBusy(false); }
  }

  async function checkIn() {
    try {
      const result = await api<UserInfo>("/api/v1/account/check-in", { method: "POST" });
      setUser(result); setNotice("签到完成；若今日已签到，额度不会重复增加");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "签到失败"); }
  }

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
    setNotice("已退出登录");
  }

  async function verifyCard(event: FormEvent) {
    event.preventDefault();
    if (!studentCard) { setError("请先选择学生证或校园卡图片"); return; }
    setBusy(true); setError(""); setNotice("");
    const data = new FormData(); data.set("file", studentCard); data.set("student_name", studentName); data.set("school", school);
    try {
      const response = await fetch("/api/v1/account/verification", {
        method: "POST", headers: { Authorization: `Bearer ${localStorage.getItem("token") ?? ""}` }, body: data,
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "认证审核失败");
      setNotice(`模型审核结果：${body.status}。${body.reason} 当前额度：${body.quota}`);
      await loadUser();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "认证审核失败"); }
    finally { setBusy(false); }
  }

  function chooseCard(event: ChangeEvent<HTMLInputElement>) { setStudentCard(event.target.files?.[0] ?? null); }

  return <main className="subPage">
    <Link className="backLink" href="/">← 返回科研助手</Link>
    <h1>我的账户</h1>
    <p>手机号注册、演示短信验证码、每日签到和多模态学生证核验。</p>
    {user ? <section className="subPageCard accountCard">
      <div className="accountHeader"><div><h2>{user.nickname}</h2><p>{user.phone || user.username} · {user.grade} · {user.major}</p></div><div className="quotaBox"><b>{user.balance}</b><span>可用额度</span></div></div>
      <p>认证状态：{user.auth_status || user.verification_status}　·　总额度：{user.quota}</p>
      <button onClick={checkIn}>每日签到 +10</button> <button type="button" onClick={logout}>退出登录</button>
      {user.is_admin && <p><Link className="backLink" href="/admin">打开管理员控制台 →</Link></p>}
      <h2>学生身份认证</h2>
      <p>图片会发送到已配置的视觉模型进行类别、学校、姓名与明显修图痕迹检查。默认使用本地模型 qwen2.5vl:7b；请先运行 model.cmd pull qwen2.5vl:7b。</p>
      <form className="verificationForm" onSubmit={verifyCard}>
        <input required value={studentName} onChange={(event) => setStudentName(event.target.value)} placeholder="证件上的姓名" />
        <input required value={school} onChange={(event) => setSchool(event.target.value)} placeholder="学校名称" />
        <input required type="file" accept="image/jpeg,image/png" onChange={chooseCard} />
        <button disabled={busy}>{busy ? "模型审核中…" : "提交模型审核"}</button>
      </form>
    </section> : <div className="accountColumns">
      <section className="subPageCard"><h2>手机号注册</h2>
        <form className="accountForm" onSubmit={register}>
          <input required value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="11 位手机号" pattern="1[3-9][0-9]{9}" />
          <div className="captchaRow"><span>{captcha?.question ?? "验证码暂不可用"}</span><input value={captchaAnswer} onChange={(event) => setCaptchaAnswer(event.target.value)} placeholder="算术答案" /><button type="button" onClick={loadCaptcha}>换一题</button></div>
          <div className="captchaRow"><input required value={smsCode} onChange={(event) => setSmsCode(event.target.value)} placeholder="6 位短信验证码" /><button type="button" disabled={!captchaValid || !/^1[3-9]\d{9}$/.test(phone) || smsCooldown > 0} onClick={sendSms}>{smsCooldown ? `${smsCooldown}s 后重试` : "获取验证码"}</button></div>
          {demoCode && <div className="demoSms">开发模式演示验证码：<b>{demoCode}</b>（已在后端控制台输出）</div>}
          <input required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="密码（至少 8 位）" />
          <input required value={nickname} onChange={(event) => setNickname(event.target.value)} placeholder="姓名 / 昵称" />
          <select value={grade} onChange={(event) => setGrade(event.target.value)}><option>本科</option><option>研究生</option><option>硕士研究生</option><option>博士研究生</option></select>
          <input required value={major} onChange={(event) => setMajor(event.target.value)} placeholder="专业" />
          <button disabled={busy}>{busy ? "处理中…" : "注册并登录"}</button>
        </form>
      </section>
      <section className="subPageCard"><h2>已有账户</h2>
        <form className="accountForm" onSubmit={login}>
          <input required value={loginPhone} onChange={(event) => setLoginPhone(event.target.value)} placeholder="手机号 / 用户名" />
          <input required type="password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} placeholder="密码" />
          <button disabled={busy}>登录</button>
        </form>
      </section>
    </div>}
    {notice && <p className="successNotice">{notice}</p>}
    {error && <p className="inlineError" role="alert">{error}</p>}
  </main>;
}
