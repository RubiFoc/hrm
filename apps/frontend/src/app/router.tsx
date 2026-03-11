import { createBrowserRouter, Navigate } from "react-router-dom";

import { AdminGuard } from "./guards/AdminGuard";
import { EmployeeGuard } from "./guards/EmployeeGuard";
import { readAuthSession } from "./auth/session";
import { RootLayout } from "../components/RootLayout";
import { AccessDeniedPage } from "../pages/AccessDeniedPage";
import { AdminEmployeeKeysManagementPage } from "../pages/AdminEmployeeKeysManagementPage";
import { AdminStaffManagementPage } from "../pages/AdminStaffManagementPage";
import { AdminShellPage } from "../pages/AdminShellPage";
import { CandidatePage } from "../pages/CandidatePage";
import { EmployeeOnboardingPage } from "../pages/EmployeeOnboardingPage";
import { HrDashboardPage } from "../pages/HrDashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { OnboardingDashboardPage } from "../pages/OnboardingDashboardPage";

function WorkspaceHomePage() {
  const session = readAuthSession();
  if (session.accessToken && session.role === "employee") {
    return <Navigate to="/employee" replace />;
  }
  if (session.accessToken && session.role === "manager") {
    return <OnboardingDashboardPage />;
  }
  return <HrDashboardPage />;
}

export const appRoutes = [
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <WorkspaceHomePage />,
      },
      {
        path: "candidate",
        element: <CandidatePage />,
      },
      {
        path: "login",
        element: <LoginPage />,
      },
      {
        path: "admin",
        element: <AdminGuard />,
        children: [
          {
            index: true,
            element: <AdminShellPage />,
          },
          {
            path: "staff",
            element: <AdminStaffManagementPage />,
          },
          {
            path: "employee-keys",
            element: <AdminEmployeeKeysManagementPage />,
          },
        ],
      },
      {
        path: "employee",
        element: <EmployeeGuard />,
        children: [
          {
            index: true,
            element: <EmployeeOnboardingPage />,
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
