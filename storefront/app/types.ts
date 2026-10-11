export type Variant = { id: number; sku: string; size: string; color: string; price: number; stock: number };
export type Gender = "women" | "men";
export type Product = { id: number; slug: string; name: string; description: string; material: string; image_url: string | null; gender: Gender; category: string; variants: Variant[] };
export type Profile = { email: string; name: string; phone: string | null; birth_date: string | null; avatar_url: string | null };
export type OrderStatus = "new" | "paid" | "packed" | "shipped" | "delivered" | "cancelled";
export type OrderSummary = { id: number; status: OrderStatus; total: number; created_at: string; items: { title: string; quantity: number; unit_price: number }[] };
