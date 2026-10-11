"use client";
import { useEffect, useState } from "react";
import { OrderSummary } from "./types";
import { copy, Locale } from "./i18n";

const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function MyOrders({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const [orders, setOrders] = useState<OrderSummary[] | null>(null);
  const [signedIn, setSignedIn] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("briefs_customer_token");
    if (!token) { setSignedIn(false); setOrders([]); return; }
    fetch(`${api}/account/orders`, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => response.ok ? response.json() : null)
      .then((data: OrderSummary[] | null) => {
        if (data) return setOrders(data);
        setSignedIn(false); setOrders([]);
      })
      .catch(() => setOrders([]));
  }, []);

  if (orders === null) return <p className="muted">…</p>;
  if (!signedIn) return <p className="muted">{t.signInFirst}</p>;
  if (orders.length === 0) return <p className="muted">{t.noOrders}</p>;

  return <div className="orders">{orders.map(order => <article className="order-card" key={order.id}>
    <header>
      <b>№{order.id}</b>
      <span className={`badge ${order.status}`}>{t.statuses[order.status]}</span>
    </header>
    <p className="muted">{new Date(order.created_at).toLocaleDateString(locale === "uk" ? "uk-UA" : "en-GB")}</p>
    {order.items.map(item => <p className="order-line" key={item.title}>{item.title} ×{item.quantity}<span>{item.unit_price * item.quantity} ₴</span></p>)}
    <b>{t.total}: {order.total} ₴</b>
  </article>)}</div>;
}
