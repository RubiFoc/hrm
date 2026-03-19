import { createBrowserRouter, Navigate } from "react-router-dom";

import { AdminGuard } from "./guards/AdminGuard";
import { EmployeeGuard } from "./guards/EmployeeGuard";
import { LeaderGuard } from "./guards/LeaderGuard";
import { readAuthSession } from "./auth/session";
import { RootLayout } from "../components/RootLayout";
import { AccessDeniedPage } from "../pages/AccessDeniedPage";
import { AccountantWorkspacePage } from "../pages/AccountantWorkspacePage";
import { AdminAuditPage } from "../pages/admin/AdminAuditPage";
import { AdminCandidatesPage } from "../pages/admin/AdminCandidatesPage";
import { AdminEmployeeKeysManagementPage } from "../pages/AdminEmployeeKeysManagementPage";
import { AdminPipelinePage } from "../pages/admin/AdminPipelinePage";
import { AdminStaffManagementPage } from "../pages/AdminStaffManagementPage";
import { AdminShellPage } from "../pages/AdminShellPage";
import { AdminVacanciesPage } from "../pages/admin/AdminVacanciesPage";
import { CandidatePage } from "../pages/CandidatePage";
import { EmployeeOnboardingPage } from "../pages/EmployeeOnboardingPage";
import { HrDashboardPage } from "../pages/HrDashboardPage";
import { LeaderWorkspacePage } from "../pages/LeaderWorkspacePage";
import { LoginPage } from "../pages/LoginPage";
import { ManagerWorkspacePage } from "../pages/ManagerWorkspacePage";

function WorkspaceHomePage() {
  const session = readAuthSession();
  if (session.accessToken && session.role === "employee") {
    return <Navigate to="/employee" replace />;
  }
  if (session.accessToken && session.role === "leader") {
    return <Navigate to="/leader" replace />;
  }
  if (session.accessToken && session.role === "manager") {
    return <ManagerWorkspacePage />;
  }
  if (session.accessToken && session.role === "accountant") {
    return <AccountantWorkspacePage />;
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
        path: "leader",
        element: <LeaderGuard />,
        children: [
          {
            index: true,
            element: <LeaderWorkspacePage />,
          },
        ],
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
          {
            path: "candidates",
            element: <AdminCandidatesPage />,
          },
          {
            path: "vacancies",
            element: <AdminVacanciesPage />,
          },
          {
            path: "pipeline",
            element: <AdminPipelinePage />,
          },
          {
            path: "audit",
            element: <AdminAuditPage />,
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
