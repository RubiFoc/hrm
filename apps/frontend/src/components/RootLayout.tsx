import { useState } from "react";
import {
  AppBar,
  Box,
  Button,
  Chip,
  Container,
  Stack,
  Tab,
  Tabs,
  Toolbar,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

import { logout } from "../api";
import { clearAuthSession, readAuthSession, resolveWorkspaceRoute } from "../app/auth/session";

/**
 * Shared top-level layout for public company pages and authenticated workspaces.
 */
export function RootLayout() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const currentLanguage = i18n.language || i18n.resolvedLanguage || "en";
  const session = readAuthSession();
  const [isLogoutPending, setIsLogoutPending] = useState(false);
  const workspacePath = resolveWorkspaceRoute(session.role);
  const tabs = [
    {
      label: t("navigation.company"),
      to: "/",
      value: "/",
    },
    {
      label: t("navigation.careers"),
      to: "/careers",
      value: "/careers",
    },
    ...(session.accessToken && session.role
      ? [
          {
            label: t("navigation.departments"),
            to: "/departments",
            value: "/departments",
          },
        ]
      : []),
    session.accessToken && session.role
      ? {
          label: t("navigation.workspace"),
          to: workspacePath,
          value: "/workspace",
        }
      : {
          label: t("loginAction"),
          to: "/login",
          value: "/login",
        },
  ];
  const activeTabValue = resolveActiveTabValue(
    location.pathname,
    Boolean(session.accessToken && session.role),
  );

  const handleLogout = async () => {
    const activeSession = readAuthSession();
    setIsLogoutPending(true);
    try {
      if (activeSession.accessToken) {
        await logout(activeSession.accessToken);
      }
    } catch {
      // Local logout should always succeed even if API logout fails.
    } finally {
      clearAuthSession();
      setIsLogoutPending(false);
      navigate("/login", { replace: true });
    }
  };

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar
        position="sticky"
        color="transparent"
        elevation={0}
        sx={{
          backdropFilter: "blur(18px)",
          backgroundColor: "rgba(247, 243, 236, 0.8)",
          borderBottom: "1px solid rgba(11, 79, 108, 0.08)",
        }}
      >
        <Toolbar sx={{ gap: 2, minHeight: { xs: 74, md: 86 } }}>
          <Stack spacing={0.25} sx={{ mr: 1, minWidth: 210 }}>
            <Typography variant="overline" color="secondary.main">
              {t("navigation.brandEyebrow")}
            </Typography>
            <Typography variant="h6">{t("appTitle")}</Typography>
          </Stack>

          <Tabs
            value={activeTabValue}
            variant="scrollable"
            allowScrollButtonsMobile
            sx={{ flex: 1, minHeight: 0 }}
          >
            {tabs.map((tab) => (
              <Tab
                key={tab.value}
                component={Link}
                label={tab.label}
                to={tab.to}
                value={tab.value}
                sx={{ minHeight: 48 }}
              />
            ))}
          </Tabs>

          {session.role ? (
            <Chip
              label={resolveRoleLabel(session.role, t)}
              color="primary"
              variant="outlined"
              sx={{ display: { xs: "none", md: "inline-flex" } }}
            />
          ) : null}

          {session.accessToken ? (
            <Button color="inherit" disabled={isLogoutPending} onClick={() => void handleLogout()}>
              {isLogoutPending ? t("logoutPendingAction") : t("logoutAction")}
            </Button>
          ) : null}

          <Button
            color="inherit"
            onClick={() => void i18n.changeLanguage(currentLanguage === "ru" ? "en" : "ru")}
          >
            {currentLanguage.toUpperCase()}
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: { xs: 3, md: 4 } }}>
        <Outlet />
      </Container>
    </Box>
  );
}

function resolveActiveTabValue(pathname: string, hasWorkspaceTab: boolean): false | string {
  if (pathname === "/careers" || pathname.startsWith("/careers/")) {
    return "/careers";
  }
  if (pathname === "/departments" || pathname.startsWith("/departments/")) {
    return "/departments";
  }
  if (
    pathname === "/hr"
    || pathname.startsWith("/hr/")
    || pathname === "/manager"
    || pathname.startsWith("/manager/")
    || pathname === "/accountant"
    || pathname.startsWith("/accountant/")
    || pathname === "/employee"
    || pathname.startsWith("/employee/")
    || pathname === "/leader"
    || pathname.startsWith("/leader/")
    || pathname === "/admin"
    || pathname.startsWith("/admin/")
  ) {
    return hasWorkspaceTab ? "/workspace" : false;
  }
  if (pathname === "/login" || pathname.startsWith("/login/")) {
    return hasWorkspaceTab ? false : "/login";
  }
  return "/";
}

function resolveRoleLabel(
  role: NonNullable<ReturnType<typeof readAuthSession>["role"]>,
  t: (key: string) => string,
): string {
  switch (role) {
    case "admin":
      return t("adminWorkspace");
    case "hr":
      return t("hrWorkspace");
    case "manager":
      return t("managerWorkspace");
    case "employee":
      return t("employeeWorkspace");
    case "leader":
      return t("leaderWorkspace");
    case "accountant":
      return t("accountantWorkspace");
    default:
      return t("navigation.workspace");
  }
}
