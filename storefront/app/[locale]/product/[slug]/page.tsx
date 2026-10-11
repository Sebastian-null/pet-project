import Image from "next/image";
import { notFound } from "next/navigation";
import { getProduct } from "../../../api";
import { categoryLabel, copy, isLocale, productCopy } from "../../../i18n";
import { ProductPicker } from "../../../ui";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale, slug } = await params;
  const product = isLocale(locale) ? await getProduct(slug) : null;
  if (!product || !isLocale(locale)) return {};
  const text = productCopy(product, locale);
  return {
    title: `${text.name} — BRIEFS`,
    description: text.description,
    openGraph: { title: text.name, description: text.description, images: product.image_url ? [product.image_url] : [] },
  };
}

export default async function ProductPage({ params }: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale, slug } = await params;
  if (!isLocale(locale)) notFound();
  const product = await getProduct(slug);
  if (!product) notFound();
  const t = copy[locale];
  const text = productCopy(product, locale);

  return <main className="detail">
    <div className={product.image_url ? "image-wrap" : "image-wrap empty"}>
      {product.image_url && <Image src={product.image_url} alt={text.name} fill priority sizes="(max-width: 800px) 100vw, 50vw" />}
    </div>
    <div className="detail-copy">
      <a className="back" href={`/${locale}`}>← {t.catalog}</a>
      <p className="eyebrow">{product.gender === "men" ? t.men : t.women} · {categoryLabel(locale, product.category)}</p>
      <h1>{text.name}</h1>
      <p className="description">{text.description}</p>
      <p className="composition"><b>{t.composition}</b><br />{text.material}</p>
      <ProductPicker product={product} locale={locale} title={text.name} />
    </div>
  </main>;
}
