import { ApiError } from "../../api";

type Translate = (key: string, options?: Record<string, unknown>) => string;

export function resolveCompensationApiError(error: unknown, t: Translate): string {
  if (error instanceof ApiError) {
    if (error.detail) {
      return t(`compensationErrors.${error.detail}`, {
        defaultValue: t(`compensationErrors.http_${error.status}`, {
          defaultValue: t("compensationErrors.generic"),
        }),
      });
    }
    return t(`compensationErrors.http_${error.status}`, {
      defaultValue: t("compensationErrors.generic"),
    });
  }
  return t("compensationErrors.generic");
}
