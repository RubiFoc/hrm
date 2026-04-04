/**
 * Lightweight typed HTTP wrapper for API calls.
 *
 * Generated OpenAPI types are created via `npm run api:types:generate`
 * into `src/api/generated/openapi-types.ts` and can be referenced in
 * higher-level API modules.
 */
import { captureFrontendHttpFailure } from "../app/observability/sentry";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export type DownloadResult = {
  contentType: string;
  filename: string;
};

export type BlobResult = {
  blob: Blob;
  contentType: string;
};

export async function apiRequest<TResponse>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(input, init);
  } catch (error) {
    captureFrontendHttpFailure(error, {
      input,
      method: init?.method,
    });
    throw error;
  }
  const rawBody = await response.text();
  const payload = parseJsonBody(rawBody);

  if (!response.ok) {
    const detail = resolveErrorDetail(payload, response.status);
    const apiError = new ApiError(response.status, detail);
    captureFrontendHttpFailure(apiError, {
      input,
      method: init?.method,
      status: response.status,
      detail,
    });
    throw apiError;
  }

  if (!rawBody.trim()) {
    return undefined as TResponse;
  }

  if (payload !== undefined) {
    return payload as TResponse;
  }
  return rawBody as TResponse;
}

/**
 * Download one binary payload as a Blob without triggering save flow.
 */
export async function apiRequestBlob(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<BlobResult> {
  let response: Response;
  try {
    response = await fetch(input, init);
  } catch (error) {
    captureFrontendHttpFailure(error, {
      input,
      method: init?.method,
    });
    throw error;
  }

  if (!response.ok) {
    const rawBody = await response.text();
    const payload = parseJsonBody(rawBody);
    const detail = resolveErrorDetail(payload, response.status);
    const apiError = new ApiError(response.status, detail);
    captureFrontendHttpFailure(apiError, {
      input,
      method: init?.method,
      status: response.status,
      detail,
    });
    throw apiError;
  }

  const blob = await response.blob();
  return {
    blob,
    contentType: response.headers.get("Content-Type") ?? "application/octet-stream",
  };
}

/**
 * Download one binary attachment and trigger browser save flow.
 */
export async function downloadFile(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<DownloadResult> {
  let response: Response;
  try {
    response = await fetch(input, init);
  } catch (error) {
    captureFrontendHttpFailure(error, {
      input,
      method: init?.method,
    });
    throw error;
  }

  if (!response.ok) {
    const rawBody = await response.text();
    const payload = parseJsonBody(rawBody);
    const detail = resolveErrorDetail(payload, response.status);
    const apiError = new ApiError(response.status, detail);
    captureFrontendHttpFailure(apiError, {
      input,
      method: init?.method,
      status: response.status,
      detail,
    });
    throw apiError;
  }

  const blob = await response.blob();
  const filename = resolveDownloadFilename(response.headers.get("Content-Disposition"));
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);

  return {
    contentType: response.headers.get("Content-Type") ?? "application/octet-stream",
    filename,
  };
}

function parseJsonBody(rawBody: string): unknown | undefined {
  if (!rawBody.trim()) {
    return undefined;
  }
  try {
    return JSON.parse(rawBody) as unknown;
  } catch {
    return undefined;
  }
}

function resolveErrorDetail(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
  }
  return `http_${status}`;
}

function resolveDownloadFilename(contentDisposition: string | null): string {
  if (!contentDisposition) {
    return "download";
  }

  const utf8FilenameMatch = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (utf8FilenameMatch?.[1]) {
    return decodeURIComponent(utf8FilenameMatch[1].trim());
  }

  const quotedFilenameMatch = contentDisposition.match(/filename\s*=\s*"([^"]+)"/i);
  if (quotedFilenameMatch?.[1]) {
    return quotedFilenameMatch[1].trim();
  }

  const plainFilenameMatch = contentDisposition.match(/filename\s*=\s*([^;]+)/i);
  if (plainFilenameMatch?.[1]) {
    return plainFilenameMatch[1].trim();
  }

  return "download";
}
