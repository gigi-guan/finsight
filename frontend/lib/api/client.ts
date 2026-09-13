const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readErrorDetail(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // keep fallback
  }
  return fallback;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    // Always get fresh balances for this milestone (no static caching).
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      await readErrorDetail(
        response,
        `API request failed (${response.status}) for ${path}`,
      ),
      response.status,
    );
  }

  return response.json() as Promise<T>;
}

export async function apiPost<TResponse, TBody>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      await readErrorDetail(
        response,
        `API request failed (${response.status}) for ${path}`,
      ),
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}

export async function apiPatch<TResponse, TBody>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      await readErrorDetail(
        response,
        `API request failed (${response.status}) for ${path}`,
      ),
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}

export async function apiPostFormData<TResponse>(
  path: string,
  formData: FormData,
): Promise<TResponse> {
  // Do not set Content-Type — the browser adds multipart boundary automatically.
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      await readErrorDetail(
        response,
        `API request failed (${response.status}) for ${path}`,
      ),
      response.status,
    );
  }

  return response.json() as Promise<TResponse>;
}
