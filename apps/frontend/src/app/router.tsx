import { createBrowserRouter } from "react-router-dom";

import { AdminGuard } from "./guards/AdminGuard";
import { RootLayout } from "../components/RootLayout";
import { AccessDeniedPage } from "../pages/AccessDeniedPage";
import { AdminShellPage } from "../pages/AdminShellPage";
import { CandidatePage } from "../pages/CandidatePage";
import { HrDashboardPage } from "../pages/HrDashboardPage";

export const appRoutes = [
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <HrDashboardPage />,
      },
      {
        path: "candidate",
        element: <CandidatePage />,
      },
      {
        path: "admin",
        element: <AdminGuard />,
        children: [
          {
            index: true,
            element: <AdminShellPage />,
          },
        ],
      },
      {
        path: "access-denied",
        element: <AccessDeniedPage />,
      },
    ],
  },
];

export const router = createBrowserRouter(appRoutes);
