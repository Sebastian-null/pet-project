/** Turns an API error response into a sentence a shopper can act on. */
export async function problem(response: Response, fallback: string): Promise<string> {
  const data = await response.json().catch(() => null);
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  return fallback;
}
