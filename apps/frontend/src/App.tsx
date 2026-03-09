import { RouterProvider } from "react-router-dom";

import { AppErrorBoundary } from "./app/observability/AppErrorBoundary";
import { router } from "./app/router";

export function App() {
  return (
    <AppErrorBoundary>
      <RouterProvider router={router} />
    </AppErrorBoundary>
  );
}
