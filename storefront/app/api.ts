import { Product } from "./types";
const url = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type ProductFilters = { q?: string; size?: string; color?: string; minPrice?: number; maxPrice?: number };

export async function getProducts(filters?: ProductFilters): Promise<Product[]> {
  const params = new URLSearchParams();
  if (filters?.q) params.set("q", filters.q);
  if (filters?.size) params.set("size", filters.size);
  if (filters?.color) params.set("color", filters.color);
  if (filters?.minPrice != null) params.set("min_price", String(filters.minPrice));
  if (filters?.maxPrice != null) params.set("max_price", String(filters.maxPrice));
  const query = params.toString();
  const response = await fetch(`${url}/products${query ? `?${query}` : ""}`, { next: { revalidate: 60 } });
  if (!response.ok) throw new Error("Could not load catalogue");
  return response.json();
}

export async function getProduct(slug: string): Promise<Product | null> {
  const response = await fetch(`${url}/products/${slug}`, { next: { revalidate: 60 } });
  return response.ok ? response.json() : null;
}

export async function getFilters(): Promise<{ sizes: string[]; colors: string[] }> {
  const response = await fetch(`${url}/products/filters`, { next: { revalidate: 300 } });
  if (!response.ok) return { sizes: [], colors: [] };
  return response.json();
}