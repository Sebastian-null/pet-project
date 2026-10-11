"use client";
import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";
import { Profile } from "./types";
import { problem } from "./errors";
import { copy, Locale } from "./i18n";

const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function Account({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const [token, setToken] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [open, setOpen] = useState(false);
  const [register, setRegister] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState("");
  const [debugCode, setDebugCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const signOut = useCallback(() => {
    for (const key of ["briefs_customer_token", "briefs_customer_email", "briefs_customer_name", "briefs_customer_phone"]) localStorage.removeItem(key);
    setToken(""); setProfile(null); setOpen(false);
  }, []);

  useEffect(() => setToken(localStorage.getItem("briefs_customer_token") || ""), []);

  useEffect(() => {
    if (!token) return setProfile(null);
    fetch(`${api}/account`, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => response.ok ? response.json() : null)
      .then((data: Profile | null) => {
        if (!data) return signOut();
        setProfile(data);
        // The checkout form reads these so a signed-in shopper does not retype them.
        localStorage.setItem("briefs_customer_name", data.name);
        localStorage.setItem("briefs_customer_phone", data.phone || "");
      });
  }, [token, signOut]);

  function saveSession(data: { access_token: string; email: string }) {
    localStorage.setItem("briefs_customer_token", data.access_token);
    localStorage.setItem("briefs_customer_email", data.email);
    setToken(data.access_token); setVerificationEmail(""); setDebugCode(""); setRegister(false); setOpen(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const form = new FormData(event.currentTarget);
    if (register && form.get("password") !== form.get("password_confirm")) return setError(t.passwordsDiffer);
    const response = await fetch(`${api}${register ? "/auth/register/request-code" : "/auth/customer/login"}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: form.get("email"), name: form.get("name") || "Customer", password: form.get("password") }),
    });
    if (!response.ok) return setError(await problem(response, t.checkFields));
    const data = await response.json();
    if (!register) return saveSession(data);
    setVerificationEmail(String(form.get("email")));
    setDebugCode(data.debug_code || "");
  }

  async function confirmCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const form = new FormData(event.currentTarget);
    const response = await fetch(`${api}/auth/register/confirm`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: verificationEmail, code: form.get("code") }),
    });
    if (!response.ok) return setError(await problem(response, t.checkFields));
    saveSession(await response.json());
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setNotice("");
    const form = new FormData(event.currentTarget);
    const response = await fetch(`${api}/account`, {
      method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: form.get("name"), phone: form.get("phone") || null, birth_date: form.get("birth_date") || null }),
    });
    if (!response.ok) return setError(await problem(response, t.checkFields));
    setProfile(await response.json()); setNotice(t.saved);
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setNotice("");
    const form = event.currentTarget;
    const data = new FormData(form);
    const response = await fetch(`${api}/account/password`, {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ current_password: data.get("current_password"), new_password: data.get("new_password") }),
    });
    if (!response.ok) return setError(await problem(response, t.checkFields));
    form.reset(); setNotice(t.passwordChanged);
  }

  async function uploadAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(""); setNotice("");
    const body = new FormData(); body.append("file", file);
    const response = await fetch(`${api}/account/avatar`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body });
    if (!response.ok) return setError(await problem(response, t.checkFields));
    setProfile(await response.json()); setNotice(t.saved);
  }

  const avatar = profile?.avatar_url || "";
  const initial = (profile?.name || profile?.email || "?").trim().charAt(0).toUpperCase();

  if (profile) return <>
    <button className="account-button chip" onClick={() => { setOpen(true); setNotice(""); setError(""); }}>
      {avatar ? <img className="avatar" src={avatar} alt="" /> : <span className="avatar fallback">{initial}</span>}
      {profile.name}
    </button>
    {open && <div className="modal"><div className="account-form">
      <button type="button" className="close" onClick={() => setOpen(false)}>×</button>
      <p className="eyebrow">BRIEFS</p>
      <h2>{t.profile}</h2>
      <p>{t.profileText}</p>
      <label className="avatar-picker">
        {avatar ? <img className="avatar large" src={avatar} alt="" /> : <span className="avatar fallback large">{initial}</span>}
        <span className="text-button">{t.changePhoto}</span>
        <input type="file" accept="image/png,image/jpeg,image/webp" onChange={uploadAvatar} hidden />
      </label>
      <form className="stack-form" onSubmit={saveProfile}>
        <label className="field">{t.name}<input name="name" required minLength={2} defaultValue={profile.name} /></label>
        <label className="field">{t.birthDate}<input name="birth_date" type="date" defaultValue={profile.birth_date || ""} /></label>
        <label className="field">{t.phone}<input name="phone" defaultValue={profile.phone || ""} /></label>
        <button className="button">{t.save}</button>
      </form>
      <details>
        <summary className="text-button">{t.changePassword}</summary>
        <form className="stack-form" onSubmit={changePassword}>
          <label className="field">{t.currentPassword}<input name="current_password" type="password" required /></label>
          <label className="field">{t.newPassword}<input name="new_password" type="password" required minLength={8} /></label>
          <button className="button">{t.save}</button>
        </form>
      </details>
      <small className="muted">{profile.email}</small>
      {notice && <small className="ok">{notice}</small>}
      {error && <small>{error}</small>}
      <button type="button" className="text-button" onClick={signOut}>{t.logout}</button>
    </div></div>}
  </>;

  return <>
    <button className="account-button" onClick={() => { setOpen(true); setError(""); }}>{t.account}</button>
    {open && <div className="modal">{verificationEmail
      ? <form className="account-form" onSubmit={confirmCode}>
          <button type="button" className="close" onClick={() => setOpen(false)}>×</button>
          <p className="eyebrow">BRIEFS</p>
          <h2>{t.verifyTitle}</h2>
          <p>{t.verifyText} <b>{verificationEmail}</b></p>
          {debugCode && <p className="dev-code">{t.devCode} <b>{debugCode}</b></p>}
          <input name="code" required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} placeholder="000000" aria-label={t.verifyTitle} />
          <button className="button">{t.register}</button>
          {error && <small>{error}</small>}
        </form>
      : <form className="account-form" onSubmit={submit}>
          <button type="button" className="close" onClick={() => setOpen(false)}>×</button>
          <p className="eyebrow">BRIEFS</p>
          <h2>{register ? t.register : t.signIn}</h2>
          <p>{t.accountText}</p>
          {register && <input required name="name" placeholder={t.name} aria-label={t.name} />}
          <input required name="email" type="email" placeholder={t.email} aria-label={t.email} />
          <input required name="password" type="password" minLength={8} placeholder={t.password} aria-label={t.password} />
          {register && <input required name="password_confirm" type="password" minLength={8} placeholder={t.repeatPassword} aria-label={t.repeatPassword} />}
          <button className="button">{register ? t.register : t.signIn}</button>
          {error && <small>{error}</small>}
          <button type="button" className="text-button" onClick={() => { setRegister(!register); setError(""); }}>{register ? t.signIn : t.register}</button>
        </form>}
    </div>}
  </>;
}
