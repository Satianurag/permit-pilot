export async function parseApiError(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return response.status === 401
      ? "Your session expired. Sign in again."
      : `Request failed (${response.status})`;
  }
  try {
    const data = JSON.parse(text) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : String(item)))
        .join("; ");
    }
  } catch {
    /* fall through */
  }
  return text;
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}
