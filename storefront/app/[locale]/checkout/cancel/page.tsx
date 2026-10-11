import Link from "next/link";
import { notFound } from "next/navigation";
import { copy, isLocale } from "../../../i18n";
export default async function CheckoutCancel({ params }: { params: Promise<{ locale: string }> }) {
  const locale = (await params).locale;
  if (!isLocale(locale)) notFound();
  const t = copy[locale];
  return <main><section className="checkout-result"><p className="eyebrow">BRIEFS</p><h1>{t.cancelTitle}</h1><p>{t.cancelText}</p><Link className="button" href={`/${locale}`}>{t.backToShop}</Link></section></main>;
}
