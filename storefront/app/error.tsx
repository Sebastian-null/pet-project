"use client";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main><section className="checkout-result">
    <p className="eyebrow">BRIEFS</p>
    <h1>Щось пішло не так</h1>
    <p>Не вдалося завантажити дані магазину. Спробуйте ще раз за хвилину.<br />Something went wrong while loading the shop.</p>
    <button className="button" onClick={reset}>Спробувати ще раз / Try again</button>
  </section></main>;
}
