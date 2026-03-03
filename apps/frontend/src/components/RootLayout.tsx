import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link, Outlet } from "react-router-dom";

export function RootLayout() {
  const { t, i18n } = useTranslation();

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
          <Button color="inherit" onClick={() => void i18n.changeLanguage(i18n.language === "ru" ? "en" : "ru") }>
            {i18n.language.toUpperCase()}
          </Button>
        </Toolbar>
      </AppBar>
      <Container sx={{ py: 4 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
