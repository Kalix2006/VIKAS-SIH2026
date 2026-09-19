/**
 * Typed API client for the VIKAS backend.
 *
 * Wraps fetch with base URL, auth headers, token management, and 401 interception.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface ApiOptions extends RequestInit {
  /** Skip automatic JSON parsing of response */
  raw?: boolean;
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

/**
 * Make an authenticated API request to the backend.
 *
 * @param path - API path (e.g., "/health", "/trainee/courses")
 * @param options - Fetch options + custom extensions
 * @returns Parsed JSON response
 */
export async function api<T = unknown>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const { raw, ...fetchOptions } = options;

  // Retrieve JWT from localStorage
  const token = localStorage.getItem("access_token");

  const headers = new Headers(fetchOptions.headers);
  if (!headers.has("Content-Type") && !(fetchOptions.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("vikas_user");

    // Redirect to login if in browser and not already on login page
    if (
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/login")
    ) {
      window.location.href = "/login";
    }
  }

  if (!response.ok) {
    let errorDetail = `API Error ${response.status}`;
    let errorData: unknown = null;
    try {
      errorData = await response.json();
      if (typeof errorData === "object" && errorData && "detail" in errorData) {
        errorDetail = String((errorData as { detail: unknown }).detail);
      }
    } catch {
      const text = await response.text();
      if (text) errorDetail = text;
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  if (raw) {
    return response as unknown as T;
  }

  return response.json() as Promise<T>;
}
