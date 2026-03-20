/**
 * Normalize a route or form value by trimming whitespace and collapsing blanks to null.
 */
export function normalizeInput(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

/**
 * Format an interview datetime using the provided timezone and a local fallback.
 */
export function formatInterviewDateTime(value: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone,
    }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
}
