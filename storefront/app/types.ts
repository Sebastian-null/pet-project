export type Variant = { id: number; sku: string; size: string; color: string; price: number; stock: number };
export type Product = { id: number; slug: string; name: string; description: string; material: string; image_url: string | null; variants: Variant[] };
