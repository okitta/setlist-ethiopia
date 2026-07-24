"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [stage, setStage] = useState<"email" | "verify" | "done">("email");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendCode(event: FormEvent) {
    event.preventDefault();
    if (!supabaseUrl || !anonKey) {
      setMessage("Sign-in is not configured yet. Add the Supabase environment variables in Vercel.");
      return;
    }
    setLoading(true);
    const response = await fetch(`${supabaseUrl}/auth/v1/otp`, {
      method: "POST",
      headers: { apikey: anonKey, "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), create_user: true }),
    });
    setLoading(false);
    if (response.ok) {
      setStage("verify");
      setMessage("We sent a verification code to your email.");
    } else {
      const body = await response.json().catch(() => ({}));
      setMessage(body.msg ?? "Unable to send the code. Please try again.");
    }
  }

  async function verifyCode(event: FormEvent) {
    event.preventDefault();
    if (!supabaseUrl || !anonKey) return;
    setLoading(true);
    const response = await fetch(`${supabaseUrl}/auth/v1/verify`, {
      method: "POST",
      headers: { apikey: anonKey, "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), token: token.trim(), type: "email" }),
    });
    const body = await response.json().catch(() => ({}));
    setLoading(false);
    if (response.ok && body.access_token) {
      window.localStorage.setItem("zema-access-token", body.access_token);
      window.localStorage.setItem("zema-refresh-token", body.refresh_token ?? "");
      setStage("done");
      setMessage("You are signed in. Your contributions can now be attributed.");
    } else {
      setMessage(body.msg ?? "That code is invalid or expired.");
    }
  }

  return (
    <main className="auth-page">
      <Link className="auth-brand" href="/"><span className="brand-mark">ዜ</span><strong>ZEMA ARCHIVE</strong></Link>
      <section className="auth-card">
        <p className="kicker"><span /> JOIN THE COMMUNITY</p>
        <h1>{stage === "done" ? "Welcome to the archive" : "Keep Ethiopia’s music alive"}</h1>
        <p>Sign in to contribute, sync saved events, and build your private concert history.</p>
        {stage === "email" && <form onSubmit={sendCode}><label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required /></label><button className="primary-action" disabled={loading}>{loading ? "Sending…" : "Send a secure code"} <span>→</span></button></form>}
        {stage === "verify" && <form onSubmit={verifyCode}><label>Verification code<input inputMode="numeric" autoComplete="one-time-code" value={token} onChange={(event) => setToken(event.target.value.replace(/\D/g, "").slice(0, 8))} placeholder="123456" required /></label><button className="primary-action" disabled={loading}>{loading ? "Checking…" : "Verify and sign in"} <span>→</span></button><button type="button" className="auth-back" onClick={() => setStage("email")}>Use another email</button></form>}
        {stage === "done" && <Link className="primary-action auth-link" href="/">Return to Zema Archive <span>→</span></Link>}
        {message && <p className="auth-message" role="status">{message}</p>}
        <small>Public browsing never requires an account. Attendance is private by default.</small>
      </section>
    </main>
  );
}
