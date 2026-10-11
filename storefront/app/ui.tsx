"use client";
import Image from "next/image";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Product } from "./types";
import { useCart } from "./cart";
import { problem } from "./errors";
import { categoryLabel, colorLabel, colorSwatch, copy, Locale, productCopy } from "./i18n";
import { Account } from "./account";
const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const localeFromPath = (path: string): Locale => path.startsWith("/en") ? "en" : "uk";
const remembered = (key: string) => typeof window === "undefined" ? "" : localStorage.getItem(key) || "";
// The URL keeps the ISO code "uk", but shoppers read "UA" as Ukrainian.
const languageLabel: Record<Locale, string> = { uk: "UA", en: "EN" };

export function SiteChrome() { const path = usePathname(), router = useRouter(), locale = localeFromPath(path), t = copy[locale], swap = locale === "uk" ? "en" : "uk"; return <header><Link className="brand" href={`/${locale}`}>BRIEFS</Link><span>{t.tagline}</span><Link href={`/${locale}/account`}>{t.myOrders}</Link><Link href={`/${locale}#catalog`}>{t.catalog}</Link><button className="language" onClick={() => router.push(path.replace(`/${locale}`, `/${swap}`))}>{languageLabel[swap]}</button><Account locale={locale} /></header>; }

export function Catalog({ products, locale }: { products: Product[]; locale: Locale }) { const t = copy[locale]; return <div className="catalog">{products.map(p => { const text = productCopy(p, locale); return <Link className="product-card" href={`/${locale}/product/${p.slug}`} key={p.id}><div className={p.image_url ? "product-photo" : "product-photo empty"}>{p.image_url && <Image src={p.image_url} alt={text.name} fill sizes="(max-width: 720px) 100vw, 50vw" />}</div><div className="card-copy"><p className="eyebrow">{p.gender === "men" ? t.men : t.women} · {categoryLabel(locale, p.category)}</p><h3>{text.name}</h3><b>{t.from} {Math.min(...p.variants.map(v => v.price))} ₴</b><p className="material">{t.composition}: {text.material}</p></div></Link>; })}</div>; }

export function FilterBar({ locale, options, current }: { locale: Locale; options: { sizes: string[]; colors: string[]; categories: string[] }; current: { [key: string]: string | undefined } }) {
  const router = useRouter(), pathname = usePathname(), t = copy[locale];
  const update = useCallback((key: string, value: string) => {
    const params = new URLSearchParams();
    Object.entries(current).forEach(([k, v]) => { if (v) params.set(k, v); });
    if (value) params.set(key, value); else params.delete(key);
    router.push(`${pathname}?${params.toString()}#catalog`);
  }, [current, pathname, router]);
  // The catalogue is rendered on the server, so searching on every keystroke fired a
  // request per character. Typing settles first, then one request goes out.
  const [typed, setTyped] = useState<string | null>(null);
  useEffect(() => {
    if (typed === null) return;
    const timer = setTimeout(() => update("q", typed.trim().slice(0, 80)), 350);
    return () => clearTimeout(timer);
  }, [typed, update]);
  return <div className="filters">
    <input defaultValue={current.q || ""} placeholder={t.searchPlaceholder} onChange={e => setTyped(e.target.value)} />
    <select value={current.gender || ""} onChange={e => update("gender", e.target.value)} aria-label={t.filters}>
      <option value="">{t.allGenders}</option>
      <option value="women">{t.women}</option>
      <option value="men">{t.men}</option>
    </select>
    <select value={current.category || ""} onChange={e => update("category", e.target.value)} aria-label={t.allCategories}>
      <option value="">{t.allCategories}</option>
      {options.categories.map(category => <option key={category} value={category}>{categoryLabel(locale, category)}</option>)}
    </select>
    <select value={current.size || ""} onChange={e => update("size", e.target.value)}>
      <option value="">{t.allSizes}</option>
      {options.sizes.map(s => <option key={s} value={s}>{s}</option>)}
    </select>
    <select value={current.color || ""} onChange={e => update("color", e.target.value)}>
      <option value="">{t.allColors}</option>
      {options.colors.map(c => <option key={c} value={c}>{colorLabel(locale, c)}</option>)}
    </select>
  </div>;
}

export function ProductPicker({ product, locale, title }: { product: Product; locale: Locale; title: string }) { const sizes = ["S", "M", "L", "XL", "XXL"], [color, setColor] = useState(product.variants[0]?.color || ""), [size, setSize] = useState(product.variants[0]?.size || "M"), variant = product.variants.find(v => v.size === size && v.color === color), { add } = useCart(), t = copy[locale], colors = [...new Set(product.variants.map(v => v.color))]; return <div className="picker"><div><label>{t.color}</label><div className="options color-options">{colors.map(item => <button className={color === item ? "selected" : ""} onClick={() => setColor(item)} key={item}><i style={{ background: colorSwatch[item] || "#d7b998" }} />{colorLabel(locale, item)}</button>)}</div></div><div><label>{t.size}</label><div className="options">{sizes.map(item => { const exists = product.variants.some(v => v.size === item && v.color === color); return <button disabled={!exists} className={size === item ? "selected" : ""} onClick={() => setSize(item)} key={item}>{item}</button>; })}</div></div>{variant ? <><p className="price">{variant.price} ₴</p><p className={variant.stock ? "availability" : "availability soldout"}>{variant.stock ? `${t.inStock} · ${variant.stock}` : t.out}</p><button className="button full" disabled={!variant.stock} onClick={() => add(variant, `${title}, ${colorLabel(locale, color)} / ${size}`)}>{t.add}</button></> : <p className="availability soldout">{t.noMatch}</p>}</div>; }


export function FloatingCart() { const { lines, remove, total } = useCart(), path = usePathname(), locale = localeFromPath(path), t = copy[locale], [open, setOpen] = useState(false), [message, setMessage] = useState(""); async function checkout(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget), token = remembered("briefs_customer_token"), response = await fetch(`${api}/orders`, { method: "POST", headers: token ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` } : { "Content-Type": "application/json" }, body: JSON.stringify({ email: form.get("email"), name: form.get("name"), phone: form.get("phone"), delivery_address: form.get("address"), locale, items: lines.map(x => ({ variant_id: x.variant.id, quantity: x.quantity })) }) }); if (!response.ok) return setMessage(await problem(response, t.checkFields)); const order = await response.json(); if (!order.payment_url) return setMessage(t.orderOk); setMessage(t.payRedirect); window.location.href = order.payment_url; } return <><button aria-label={t.cart} className="cart-toggle" onClick={() => setOpen(true)}><svg viewBox="0 0 24 24"><path d="M3 4h2l2.2 10.2a2 2 0 0 0 2 1.6h7.6a2 2 0 0 0 1.9-1.4L20 8H7"/><circle cx="10" cy="20" r="1"/><circle cx="17" cy="20" r="1"/></svg>{lines.length > 0 && <em>{lines.length}</em>}</button>{open && <div className="modal"><form className="checkout" onSubmit={checkout}><button type="button" className="close" onClick={() => setOpen(false)}>×</button><h2>{t.checkout}</h2>{lines.length ? lines.map(x => <p className="bag-line" key={x.variant.id}>{x.title} ×{x.quantity}<button type="button" onClick={() => remove(x.variant.id)}>{t.remove}</button></p>) : <p>{t.cart} — 0</p>}<b>{t.total}: {total} ₴</b>{lines.length > 0 && <><input name="name" required minLength={2} defaultValue={remembered("briefs_customer_name")} placeholder={t.name} aria-label={t.name}/><input name="email" type="email" required defaultValue={remembered("briefs_customer_email")} placeholder={t.email} aria-label={t.email}/><input name="phone" defaultValue={remembered("briefs_customer_phone")} placeholder={t.phone} aria-label={t.phone}/><input name="address" required minLength={8} placeholder={t.addressExample} aria-label={t.address}/><button className="button">{t.confirm}</button></>}{message && <p>{message}</p>}</form></div>}</>; }
