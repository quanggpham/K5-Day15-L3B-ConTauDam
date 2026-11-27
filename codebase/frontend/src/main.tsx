import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { createClient, type SupabaseClient, type Session } from "@supabase/supabase-js";
import "./style.css";

function App() {
  const [client, setClient] = useState<SupabaseClient | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [message, setMessage] = useState("Đang kết nối...");
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
  return <main><h1>LearningPulse</h1>{message && <p role="status">{message}</p>}{session ? <><p>Đã đăng nhập: {session.user.email}</p><button onClick={signOut}>Đăng xuất</button><p>Chức năng phân tích đang được phát triển.</p></> : client && <form onSubmit={signIn}><label>Email <input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} /></label><label>Mật khẩu <input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label><button type="submit">Đăng nhập</button></form>}</main>;
}
createRoot(document.getElementById("root")!).render(<App />);
