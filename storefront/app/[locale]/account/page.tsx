import Link from "next/link";
import { notFound } from "next/navigation";
import { copy, isLocale } from "../../i18n";
import { MyOrders } from "../../orders";

export default async function AccountPage({ params }: { params: Promise<{ locale: string }> }) {
  const locale = (await params).locale;
  if (!isLocale(locale)) notFound();
  const t = copy[locale];
  return <main><section className="account-page">
    <Link className="back" href={`/${locale}`}>← {t.catalog}</Link>
    <p className="eyebrow">BRIEFS</p>
    <h1>{t.myOrders}</h1>
    <MyOrders locale={locale} />
  </section></main>;
}
