import type {
  Account,
  AccountCreate,
  AccountUpdate,
  Category,
  CategoryCreate,
  CategoryGroup,
  CategoryUpdate,
  Payee,
  PayeeCreate,
  PayeeUpdate,
  Transaction,
  TransactionCreate,
  TransactionQuery,
  TransactionUpdate,
  UUID,
} from "@/lib/types";

// Same origin: both the Astro dev server and the nginx image proxy /api to the API.
const BASE_URL = "";

type QueryValue = string | number | boolean | null | undefined;

/** A response the API refused, carrying the message it explained itself with. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await failure(response));
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

/** Our own handlers answer with `message`; FastAPI's validation with `detail`. */
async function failure(response: Response): Promise<string> {
  const body = await response.text();
  try {
    const parsed = JSON.parse(body) as {
      message?: string;
      detail?: string | { msg?: string }[];
    };
    if (parsed.message) return parsed.message;
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail.map((entry) => entry.msg ?? "invalid").join("; ");
    }
  } catch {
    // Not JSON: fall through to the raw body.
  }
  return body || `request failed with ${response.status}`;
}

function query(params: Record<string, QueryValue> = {}): string {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(name, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

const send = (method: string, payload: unknown): RequestInit => ({
  method,
  body: JSON.stringify(payload),
});

export const api = {
  accounts: {
    list: (options: { include_closed?: boolean } = {}) =>
      request<Account[]>(`/accounts${query(options)}`),
    get: (id: UUID) => request<Account>(`/accounts/${id}`),
    create: (payload: AccountCreate) => request<Account>("/accounts", send("POST", payload)),
    update: (id: UUID, payload: AccountUpdate) =>
      request<Account>(`/accounts/${id}`, send("PATCH", payload)),
    remove: (id: UUID) => request<void>(`/accounts/${id}`, { method: "DELETE" }),
  },
  categories: {
    list: (options: { include_hidden?: boolean } = {}) =>
      request<CategoryGroup[]>(`/categories${query(options)}`),
    get: (id: UUID) => request<Category>(`/categories/${id}`),
    create: (payload: CategoryCreate) =>
      request<Category>("/categories", send("POST", payload)),
    update: (id: UUID, payload: CategoryUpdate) =>
      request<Category>(`/categories/${id}`, send("PATCH", payload)),
    remove: (id: UUID) => request<void>(`/categories/${id}`, { method: "DELETE" }),
  },
  payees: {
    list: (options: { search?: string } = {}) => request<Payee[]>(`/payees${query(options)}`),
    get: (id: UUID) => request<Payee>(`/payees/${id}`),
    create: (payload: PayeeCreate) => request<Payee>("/payees", send("POST", payload)),
    update: (id: UUID, payload: PayeeUpdate) =>
      request<Payee>(`/payees/${id}`, send("PATCH", payload)),
    remove: (id: UUID) => request<void>(`/payees/${id}`, { method: "DELETE" }),
  },
  transactions: {
    list: (options: TransactionQuery = {}) =>
      request<Transaction[]>(`/transactions${query(options)}`),
    get: (id: UUID) => request<Transaction>(`/transactions/${id}`),
    create: (payload: TransactionCreate) =>
      request<Transaction>("/transactions", send("POST", payload)),
    update: (id: UUID, payload: TransactionUpdate) =>
      request<Transaction>(`/transactions/${id}`, send("PATCH", payload)),
    remove: (id: UUID) => request<void>(`/transactions/${id}`, { method: "DELETE" }),
  },
};
