import Link from "next/link";
import { notFound } from "next/navigation";
import { getPaymentStatus } from "../../../api";
import { ClearCart } from "../../../clear-cart";
import { copy, isLocale } from "../../../i18n";
export const dynamic = "force-dynamic";
export default async function CheckoutSuccess({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<{ session_id?: string }> }) {
  const locale = (await params).locale;
  if (!isLocale(locale)) notFound();
  const t = copy[locale];
  const sessionId = (await searchParams).session_id;
  const payment = sessionId ? await getPaymentStatus(sessionId) : null;
  const paid = payment?.status === "paid";
  return <main><ClearCart /><section className="checkout-result"><p className="eyebrow">BRIEFS</p><h1>{paid ? t.paidTitle : t.pendingTitle}</h1><p>{paid ? t.paidText : t.pendingText}</p>{payment && <p className="order-ref">{t.orderNumber} №{payment.order_id} — {payment.total} ₴</p>}<Link className="button" href={`/${locale}`}>{t.backToShop}</Link></section></main>;
}
