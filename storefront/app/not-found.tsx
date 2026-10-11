import Link from "next/link";

export default function NotFound() {
  return <main><section className="checkout-result">
    <p className="eyebrow">404</p>
    <h1>Сторінку не знайдено</h1>
    <p>Схоже, посилання застаріло або мову вказано неправильно.<br />This page does not exist.</p>
    <Link className="button" href="/uk">На головну / Home</Link>
  </section></main>;
}
