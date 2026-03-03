import { createBrowserRouter } from "react-router-dom";

import { RootLayout } from "../components/RootLayout";
import { CandidatePage } from "../pages/CandidatePage";
import { HrDashboardPage } from "../pages/HrDashboardPage";

export const router = createBrowserRouter([
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
    ],
  },
]);
