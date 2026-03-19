import type { ApiError } from "../../api";

export type TranslationFn = (key: string, options?: Record<string, unknown>) => string;

/**
 * Normalize free-form filter input into an optional query value.
 *
 * Inputs:
 * - `value`: raw user-entered string from a text field.
 *
 * Outputs:
 * - trimmed string when non-empty, otherwise `undefined` for omitted query params.
 */
export function normalizeFilterValue(value: string): string | undefined {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
}

/**
 * Render a backend timestamp into the current locale or a placeholder.
 *
 * Inputs:
 * - `value`: ISO timestamp string or nullish value.
 * - `fallback`: text shown when the value is missing or invalid.
 *
 * Outputs:
 * - localized date/time string or the provided fallback.
 */
export function formatDateTime(value: string | null | undefined, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

/**
 * Render a backend date into the current locale or a placeholder.
 *
 * Inputs:
 * - `value`: ISO date string or nullish value.
 * - `fallback`: text shown when the value is missing or invalid.
 *
 * Outputs:
 * - localized date string or the provided fallback.
 */
export function formatDate(value: string | null | undefined, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

/**
 * Convert a backend error into a localized admin message.
 *
 * Inputs:
 * - `error`: thrown API error or unexpected exception.
 * - `t`: translation function.
 * - `translationPrefix`: translation key prefix for the current admin page.
 * - `fallbackKey`: fallback translation key suffix for unmapped errors.
 *
 * Outputs:
 * - localized, user-readable error string.
 */
export function resolveApiErrorMessage(
  error: unknown,
  t: TranslationFn,
  translationPrefix: string,
  fallbackKey = "validation_failed",
): string {
  if (isApiError(error)) {
    const detailKey = `${translationPrefix}.errors.${error.detail}`;
    const mapped = t(detailKey);
    if (mapped !== detailKey) {
      return mapped;
    }
    const statusKey = `${translationPrefix}.errors.http_${error.status}`;
    const statusMapped = t(statusKey);
    if (statusMapped !== statusKey) {
      return statusMapped;
    }
  }
  return t(`${translationPrefix}.errors.${fallbackKey}`);
}

function isApiError(error: unknown): error is ApiError {
  return Boolean(error && typeof error === "object" && "status" in error && "detail" in error);
}
