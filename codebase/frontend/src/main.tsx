import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { createClient, type SupabaseClient, type Session } from "@supabase/supabase-js";
import "./style.css";

function App() {
  const [client, setClient] = useState<SupabaseClient | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [message, setMessage] = useState("Đang kết nối...");
  const [authorized, setAuthorized] = useState(false);
  const [lessons, setLessons] = useState<string[]>([]);
  const [selected, setSelected] = useState("");
  const [report, setReport] = useState<{notice:string; priority:{kc_code:string; incorrect_count:number; graded_count:number}[]; metrics: {kc_code:string; insufficient_data?:boolean; graded_count?:number; incorrect_count?:number; ungraded_count?:number; incorrect_rate?:number|null}[]} | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  useEffect(() => {
    let active = true;
    let unsubscribe = () => {};
    fetch("/api/config").then(r => { if (!r.ok) throw Error(); return r.json(); }).then(config => {
      if (!active) return;
      if (!config.supabase_url || !config.supabase_publishable_key) { setMessage("Chưa cấu hình Supabase."); return; }
      const supabase = createClient(config.supabase_url, config.supabase_publishable_key);
      setClient(supabase);
      supabase.auth.getSession().then(({ data, error }) => { if (active) { setSession(data.session); setMessage(error ? error.message : ""); } });
      const { data } = supabase.auth.onAuthStateChange((_event, value) => { if (active) setSession(value); });
      unsubscribe = () => data.subscription.unsubscribe();
    }).catch(() => { if (active) setMessage("Không kết nối được backend."); });
    return () => { active = false; unsubscribe(); };
  }, []);
  useEffect(() => {
    setAuthorized(false);
    if (!session) return;
    let active = true;
    fetch("/api/me", { headers: { Authorization: `Bearer ${session.access_token}` } })
      .then(response => {
        if (!active) return;
        if (response.ok) { setAuthorized(true); setMessage(""); }
        else setMessage(response.status === 403 ? "Tài khoản chưa được cấp quyền." : "Không xác minh được quyền truy cập.");
      })
      .catch(() => { if (active) setMessage("Không xác minh được quyền truy cập."); });
    return () => { active = false; };
  }, [session]);
  useEffect(() => {
    if (!authorized || !session) { setLessons([]); setReport(null); return; }
    let active = true;
    fetch("/api/lessons", { headers: { Authorization: `Bearer ${session.access_token}` } })
      .then(async response => { if (!response.ok) throw Error(); const data = await response.json(); if (active) setLessons(data); })
      .catch(() => { if (active) setMessage("Chưa có dữ liệu tổng hợp. Hãy liên hệ quản trị viên."); });
    return () => { active = false; };
  }, [authorized, session]);
  async function loadReport() {
    if (!session || !selected) return;
    setReport(null);
    try {
      const response = await fetch(`/api/lessons/${encodeURIComponent(selected)}`, { headers: { Authorization: `Bearer ${session.access_token}` } });
      if (!response.ok) throw Error();
      setReport(await response.json());
    } catch { setMessage("Không tải được báo cáo."); }
  }
  async function saveDraft() {
    if (!client || !session || !report || !authorized || !selected) return;
    const { error } = await client.from("analysis_runs").insert({ user_id: session.user.id, lesson_id: selected, status: "draft", metrics_snapshot: report });
    setMessage(error ? "Không lưu được bản nháp." : "Đã lưu bản nháp báo cáo.");
  }
  async function signIn(event: React.FormEvent) {
    event.preventDefault();
    if (!client) return;
    const { error } = await client.auth.signInWithPassword({ email, password });
    setMessage(error ? error.message : "");
  }
  async function signOut() {
    if (!client) return;
    const { error } = await client.auth.signOut();
    setMessage(error ? error.message : "");
  }
  return <main><h1>LearningPulse</h1>{message && <p role="status">{message}</p>}{session ? <><p>Đã đăng nhập: {session.user.email}</p><button onClick={signOut}>Đăng xuất</button>{authorized && <section><label>Bài học <select value={selected} onChange={e => setSelected(e.target.value)}><option value="">Chọn bài học</option>{lessons.map(lesson => <option key={lesson} value={lesson}>{lesson}</option>)}</select></label><button disabled={!selected} onClick={loadReport}>Xem báo cáo</button>{report && <><p>{report.notice}</p><h2>Thứ tự theo tỷ lệ sai lần đầu</h2><ol>{report.priority.map(row => <li key={row.kc_code}>{row.kc_code}: {row.incorrect_count}/{row.graded_count} lượt sai</li>)}</ol><button onClick={saveDraft}>Lưu bản nháp</button><ul>{report.metrics.map(row => <li key={row.kc_code}>{row.kc_code}: {row.insufficient_data ? "Chưa đủ 5 học viên" : `${row.incorrect_count}/${row.graded_count} lượt sai; ${row.ungraded_count} lượt chưa chấm`}</li>)}</ul></>}</section>}</> : client && <form onSubmit={signIn}><label>Email <input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} /></label><label>Mật khẩu <input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label><button type="submit">Đăng nhập</button></form>}</main>;
}
createRoot(document.getElementById("root")!).render(<App />);
