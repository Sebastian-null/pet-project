"use client";
import { createContext, useContext, useMemo, useState } from "react";
import { Variant } from "./types";
import { FloatingCart } from "./ui";
type Line = { variant: Variant; title: string; quantity: number };
type Cart = { lines: Line[]; add: (variant: Variant, title: string) => void; remove: (id: number) => void; total: number };
const CartContext = createContext<Cart | null>(null);
export function CartProvider({ children }: { children: React.ReactNode }) { const [lines, setLines] = useState<Line[]>([]); const value = useMemo(() => ({ lines, add(variant: Variant, title: string) { setLines(old => { const found = old.find(x => x.variant.id === variant.id); return found ? old.map(x => x.variant.id === variant.id ? { ...x, quantity: Math.min(x.quantity + 1, variant.stock) } : x) : [...old, { variant, title, quantity: 1 }]; }); }, remove(id: number) { setLines(old => old.filter(x => x.variant.id !== id)); }, total: lines.reduce((sum, x) => sum + x.variant.price * x.quantity, 0) }), [lines]); return <CartContext.Provider value={value}>{children}<FloatingCart /></CartContext.Provider>; }
export function useCart() { const context = useContext(CartContext); if (!context) throw new Error("CartProvider missing"); return context; }
