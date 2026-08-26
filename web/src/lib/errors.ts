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
  const raw =
    typeof error === "string" && error.trim()
      ? error
      : error instanceof Error
        ? error.message
        : "Something went wrong";

  const lower = raw.toLowerCase();
  if (lower.includes("failed to fetch") || lower.includes("networkerror") || lower.includes("network abort")) {
    return "Can't reach Permit Pilot. Check your connection and try again.";
  }
  if (lower.includes("vertex") || lower.includes("model unavailable") || lower.includes("502")) {
    return "The briefing model is unavailable right now. Department reviews are unaffected.";
  }
  if (lower.includes("firestore write failed") || lower.includes("500") || lower.includes("503")) {
    return "Permit Pilot couldn't complete that. Try again — nothing was saved.";
  }
  if (lower.includes("session expired") || lower.includes("credentials")) {
    return "Your session expired. Sign in again.";
  }
  return raw;
}

export function isNotFoundError(message: string): boolean {
  const lower = message.toLowerCase();
  return lower.includes("not found") || lower.includes("404");
}
