import { getProducts, getFilters } from "../api";
import { Catalog, FilterBar } from "../ui";
import { copy, isLocale } from "../i18n";
export const dynamic = "force-dynamic";
export default async function Home({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<{ [key: string]: string | undefined }> }) {
  const locale = (await params).locale;
  if (!isLocale(locale)) return null;
  const sp = await searchParams;
  const t = copy[locale];
  const filters = { q: sp.q, size: sp.size, color: sp.color, minPrice: sp.min_price ? Number(sp.min_price) : undefined, maxPrice: sp.max_price ? Number(sp.max_price) : undefined };
  const [products, options] = await Promise.all([getProducts(filters), getFilters()]);
  return <main><section className="hero"><div className="hero-copy"><p className="eyebrow">{t.heroKicker}</p><h1>{t.hero.split("\n").map(x => <span key={x}>{x}<br /></span>)}</h1><p>{t.heroText}</p><a className="button" href="#catalog">{t.shop}</a></div><div className="hero-orb" /></section><section id="catalog"><div className="section-title"><div><p className="eyebrow">{t.collection}</p><h2>{t.favourites}</h2></div><span>{products.length} {t.models}</span></div><FilterBar locale={locale} options={options} current={sp} /><Catalog products={products} locale={locale} /></section></main>;
}