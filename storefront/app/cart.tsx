"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Variant } from "./types";
import { FloatingCart } from "./ui";

type Line = { variant: Variant; title: string; quantity: number };
type Cart = { lines: Line[]; add: (variant: Variant, title: string) => void; remove: (id: number) => void; clear: () => void; total: number; restored: boolean };

const CartContext = createContext<Cart | null>(null);
const STORAGE_KEY = "briefs_cart";

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [lines, setLines] = useState<Line[]>([]);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) setLines(JSON.parse(saved));
    } catch {
      // Private browsing can block storage; an empty basket is a fine fallback.
    }
    setRestored(true);
  }, []);

  useEffect(() => {
    if (!restored) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
    } catch {
      // Ignore: the basket still works for this page view.
    }
  }, [lines, restored]);

  // Identities stay stable so effects that depend on them (clearing after payment) run once.
  const add = useCallback((variant: Variant, title: string) => {
    setLines(old => {
      const found = old.find(x => x.variant.id === variant.id);
      return found
        ? old.map(x => x.variant.id === variant.id ? { ...x, quantity: Math.min(x.quantity + 1, variant.stock) } : x)
        : [...old, { variant, title, quantity: 1 }];
    });
  }, []);
  const remove = useCallback((id: number) => setLines(old => old.filter(x => x.variant.id !== id)), []);
  const clear = useCallback(() => setLines(old => old.length ? [] : old), []);

  const value = useMemo<Cart>(() => ({
    lines, add, remove, clear, restored,
    total: lines.reduce((sum, x) => sum + x.variant.price * x.quantity, 0),
  }), [lines, add, remove, clear, restored]);

  return <CartContext.Provider value={value}>{children}<FloatingCart /></CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("CartProvider missing");
  return context;
}
