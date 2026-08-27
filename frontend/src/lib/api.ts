import type { Account, CategoryGroup, Payee, Transaction } from "@/lib/types";

// Same origin: both the Astro dev server and the nginx image proxy /api to the API.
const BASE_URL = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status} ${detail}`);
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  accounts: () => request<Account[]>("/accounts"),
  categories: () => request<CategoryGroup[]>("/categories"),
  payees: () => request<Payee[]>("/payees"),
  transactions: (query: Record<string, string> = {}) => {
    const search = new URLSearchParams(query).toString();
    return request<Transaction[]>(`/transactions${search ? `?${search}` : ""}`);
  },
};
