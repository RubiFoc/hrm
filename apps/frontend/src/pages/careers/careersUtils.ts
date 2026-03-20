/**
 * Build the canonical public vacancy detail URL for the careers surface.
 *
 * Inputs:
 * - `vacancyId`: vacancy UUID selected from the public board or deep link.
 * - `vacancyTitle`: optional display-only title used as a fallback hint.
 *
 * Outputs:
 * - A canonical `/careers/:vacancyId` path with an optional `vacancyTitle` query string.
 */
export function buildVacancyDetailPath(vacancyId: string, vacancyTitle?: string | null): string {
  const normalizedVacancyId = vacancyId.trim();
  const normalizedTitle = vacancyTitle?.trim();
  if (!normalizedTitle) {
    return `/careers/${normalizedVacancyId}`;
  }

  const searchParams = new URLSearchParams({
    vacancyTitle: normalizedTitle,
  });
  return `/careers/${normalizedVacancyId}?${searchParams.toString()}`;
}

/**
 * Format a localized date label for public careers surfaces.
 *
 * Inputs:
 * - `value`: ISO datetime string.
 * - `locale`: current UI locale.
 *
 * Outputs:
 * - Human-readable date label in the active locale.
 */
export function formatDateLabel(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value));
}

/**
 * Normalize optional query-string input into a trimmed string or null.
 *
 * Inputs:
 * - `value`: raw query-string value.
 *
 * Outputs:
 * - Trimmed string, or `null` when the input is empty.
 */
export function normalizeInput(value: string | null): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}
