import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as Sentry from "@sentry/react";

import { App } from "./App";
import "./styles.css";
import "./app/i18n";

const dsn = normalizeEnvValue(import.meta.env.VITE_SENTRY_DSN);
if (dsn) {
  Sentry.init({
    dsn,
    environment: normalizeEnvValue(import.meta.env.VITE_SENTRY_ENVIRONMENT) ?? "local-compose",
    release: normalizeEnvValue(import.meta.env.VITE_SENTRY_RELEASE),
    integrations: [Sentry.browserTracingIntegration()],
    tracePropagationTargets: resolveTracePropagationTargets(import.meta.env.VITE_API_BASE_URL),
    tracesSampleRate: resolveTracesSampleRate(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE),
  });
}

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);

function normalizeEnvValue(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized ? normalized : undefined;
}

function resolveTracesSampleRate(rawValue: string | undefined): number {
  const parsedValue = Number.parseFloat(rawValue ?? "");
  if (Number.isFinite(parsedValue) && parsedValue >= 0 && parsedValue <= 1) {
    return parsedValue;
  }
  return 0.2;
}

function resolveTracePropagationTargets(apiBaseUrl: string | undefined): Array<string | RegExp> {
  const targets: Array<string | RegExp> = [
    "localhost",
    /^https?:\/\/localhost(?::\d+)?\//,
    /^\/api\//,
  ];
  const normalized = normalizeEnvValue(apiBaseUrl);
  if (normalized) {
    targets.push(normalized);
  }
  return targets;
}
