import { createBrowserRouter } from "react-router-dom";

import { AdminGuard } from "./guards/AdminGuard";
import { EmployeeGuard } from "./guards/EmployeeGuard";
import { LeaderGuard } from "./guards/LeaderGuard";
import { RoleGuard } from "./guards/RoleGuard";
import { RootLayout } from "../components/RootLayout";
import { AccessDeniedPage } from "../pages/AccessDeniedPage";
import { AccountantWorkspacePage } from "../pages/AccountantWorkspacePage";
import { AdminAuditPage } from "../pages/admin/AdminAuditPage";
import { AdminCandidatesPage } from "../pages/admin/AdminCandidatesPage";
import { AdminEmployeeKeysManagementPage } from "../pages/AdminEmployeeKeysManagementPage";
import { AdminObservabilityPage } from "../pages/admin/AdminObservabilityPage";
import { AdminPipelinePage } from "../pages/admin/AdminPipelinePage";
import { AdminStaffManagementPage } from "../pages/AdminStaffManagementPage";
import { AdminShellPage } from "../pages/AdminShellPage";
import { AdminVacanciesPage } from "../pages/admin/AdminVacanciesPage";
import { CandidatePage } from "../pages/CandidatePage";
import { CareersPage } from "../pages/CareersPage";
import { CareersVacancyPage } from "../pages/CareersVacancyPage";
import { CompanyHomePage } from "../pages/CompanyHomePage";
import { EmployeeOnboardingPage } from "../pages/EmployeeOnboardingPage";
import { EmployeeDirectoryPage } from "../pages/employee/EmployeeDirectoryPage";
import { EmployeeDirectoryProfilePage } from "../pages/employee/EmployeeDirectoryProfilePage";
import { EmployeeReferralsPage } from "../pages/employee/EmployeeReferralsPage";
import { HrDashboardPage } from "../pages/HrDashboardPage";
import { HrInterviewsPage } from "../pages/hr/HrInterviewsPage";
import { HrOffersPage } from "../pages/hr/HrOffersPage";
import { HrOverviewPage } from "../pages/hr/HrOverviewPage";
import { HrPipelinePage } from "../pages/hr/HrPipelinePage";
import { HrReferralsPage } from "../pages/hr/HrReferralsPage";
import { HrVacanciesPage } from "../pages/hr/HrVacanciesPage";
import { LeaderWorkspacePage } from "../pages/LeaderWorkspacePage";
import { LoginPage } from "../pages/LoginPage";
import { ManagerReferralsPage } from "../pages/manager/ManagerReferralsPage";
import { ManagerWorkspacePage } from "../pages/ManagerWorkspacePage";
import { CandidateApplyPage } from "../pages/candidate/CandidateApplyPage";
import { CandidateInterviewRegistrationPage } from "../pages/candidate/CandidateInterviewRegistrationPage";

export const appRoutes = [
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <CompanyHomePage />,
      },
      {
        path: "careers",
        element: <CareersPage />,
      },
      {
        path: "careers/:vacancyId",
        element: <CareersVacancyPage />,
      },
      {
        path: "candidate",
        element: <CandidatePage />,
      },
      {
        path: "candidate/apply",
        element: <CandidateApplyPage />,
      },
      {
        path: "candidate/interview/:interviewToken",
        element: <CandidateInterviewRegistrationPage />,
      },
      {
        path: "hr",
        element: <RoleGuard allowedRoles={["admin", "hr"]} />,
        children: [
          {
            index: true,
            element: <HrOverviewPage />,
          },
          {
            path: "vacancies",
            element: <HrVacanciesPage />,
          },
          {
            path: "pipeline",
            element: <HrPipelinePage />,
          },
          {
            path: "interviews",
            element: <HrInterviewsPage />,
          },
          {
            path: "offers",
            element: <HrOffersPage />,
          },
          {
            path: "referrals",
            element: <HrReferralsPage />,
          },
          {
            path: "workbench",
            element: <HrDashboardPage />,
          },
        ],
      },
      {
        path: "manager",
        element: <RoleGuard allowedRoles={["manager"]} />,
        children: [
          {
            index: true,
            element: <ManagerWorkspacePage />,
          },
          {
            path: "referrals",
            element: <ManagerReferralsPage />,
          },
        ],
      },
      {
        path: "accountant",
        element: <RoleGuard allowedRoles={["accountant"]} />,
        children: [
          {
            index: true,
            element: <AccountantWorkspacePage />,
          },
        ],
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
          {
            path: "observability",
            element: <AdminObservabilityPage />,
          },
        ],
      },
      {
        path: "employee",
        element: (
          <RoleGuard
            allowedRoles={["admin", "hr", "manager", "employee", "leader", "accountant"]}
          />
        ),
        children: [
          {
            element: <EmployeeGuard />,
            children: [
              {
                index: true,
                element: <EmployeeOnboardingPage />,
              },
              {
                path: "referrals",
                element: <EmployeeReferralsPage />,
              },
            ],
          },
          {
            path: "directory",
            element: <EmployeeDirectoryPage />,
          },
          {
            path: "directory/:employeeId",
            element: <EmployeeDirectoryProfilePage />,
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
