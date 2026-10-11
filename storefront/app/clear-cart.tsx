"use client";
import { useEffect } from "react";
import { useCart } from "./cart";

/**
 * Empties the basket once the customer lands back from a completed payment.
 * It waits for `restored`, because React runs this child effect before the
 * provider reloads the saved basket — clearing earlier would be undone.
 */
export function ClearCart() {
  const { clear, restored } = useCart();
  useEffect(() => {
    if (restored) clear();
  }, [restored, clear]);
  return null;
}
