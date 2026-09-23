import { notFound } from "next/navigation";
import Image from "next/image";
import { getProduct } from "../../../api";
import { ProductPicker } from "../../../ui";
import { copy, isLocale, productText } from "../../../i18n";
export const dynamic = "force-dynamic";
export default async function ProductPage({ params }: { params: Promise<{locale: string; slug: string}> }) { const { locale, slug } = await params; if (!isLocale(locale)) notFound(); const product = await getProduct(slug); if (!product) notFound(); const text = productText[slug as keyof typeof productText]?.[locale] || { name: product.name, description: product.description, material: product.material, gender: "men" }; return <main className="detail"><div className="image-wrap">{product.image_url && <Image src={product.image_url} alt={text.name} fill priority sizes="(max-width: 800px) 100vw, 50vw" />}</div><div className="detail-copy"><a className="back" href={`/${locale}`}>← {copy[locale].catalog}</a><p className="eyebrow">{text.gender === "men" ? copy[locale].men : copy[locale].women}</p><h1>{text.name}</h1><p className="description">{text.description}</p><p className="composition"><b>{copy[locale].composition}</b><br />{text.material}</p><ProductPicker product={product} locale={locale} title={text.name} /></div></main>; }
