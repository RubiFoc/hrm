import { useState } from "react";
import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useNavigate } from "react-router-dom";

import { logout } from "../api";
import { clearAuthSession, readAuthSession } from "../app/auth/session";

export function RootLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const currentLanguage = i18n.language || i18n.resolvedLanguage || "en";
  const session = readAuthSession();
  const [isLogoutPending, setIsLogoutPending] = useState(false);

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
    <Box>
      <AppBar position="static" color="primary">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            {t("appTitle")}
          </Typography>
          <Button color="inherit" component={Link} to="/">
            {t("hrWorkspace")}
          </Button>
          <Button color="inherit" component={Link} to="/candidate">
            {t("candidateWorkspace")}
          </Button>
          <Button color="inherit" component={Link} to="/admin">
            {t("adminWorkspace")}
          </Button>
          {session.accessToken ? (
            <Button color="inherit" disabled={isLogoutPending} onClick={() => void handleLogout()}>
              {isLogoutPending ? t("logoutPendingAction") : t("logoutAction")}
            </Button>
          ) : (
            <Button color="inherit" component={Link} to="/login">
              {t("loginAction")}
            </Button>
          )}
          <Button
            color="inherit"
            onClick={() => void i18n.changeLanguage(currentLanguage === "ru" ? "en" : "ru")}
          >
            {currentLanguage.toUpperCase()}
          </Button>
        </Toolbar>
      </AppBar>
      <Container sx={{ py: 4 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
