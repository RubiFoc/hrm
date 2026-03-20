import { alpha, createTheme } from "@mui/material/styles";

/**
 * Shared application theme for the refreshed company, careers, and role workspaces.
 */
export const appTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0b4f6c",
      light: "#4f89a3",
      dark: "#08384d",
      contrastText: "#f7f2ea",
    },
    secondary: {
      main: "#d17b49",
      light: "#e0a17c",
      dark: "#8d4f2c",
      contrastText: "#fff8f2",
    },
    success: {
      main: "#2f8f6b",
    },
    warning: {
      main: "#c37b27",
    },
    error: {
      main: "#b85448",
    },
    background: {
      default: "#f4efe7",
      paper: "#fffdf9",
    },
    text: {
      primary: "#142434",
      secondary: "#56687a",
    },
    divider: alpha("#0b4f6c", 0.12),
  },
  shape: {
    borderRadius: 24,
  },
  typography: {
    fontFamily: '"IBM Plex Sans", "Segoe UI", sans-serif',
    h1: {
      fontFamily: '"Iowan Old Style", "Palatino Linotype", Georgia, serif',
      fontWeight: 700,
      letterSpacing: "-0.03em",
    },
    h2: {
      fontFamily: '"Iowan Old Style", "Palatino Linotype", Georgia, serif',
      fontWeight: 700,
      letterSpacing: "-0.03em",
    },
    h3: {
      fontFamily: '"Iowan Old Style", "Palatino Linotype", Georgia, serif',
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    h4: {
      fontFamily: '"Iowan Old Style", "Palatino Linotype", Georgia, serif',
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    h5: {
      fontFamily: '"Iowan Old Style", "Palatino Linotype", Georgia, serif',
      fontWeight: 700,
    },
    h6: {
      fontWeight: 700,
    },
    button: {
      fontWeight: 700,
      letterSpacing: "0.01em",
      textTransform: "none",
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        ":root": {
          colorScheme: "light",
        },
        body: {
          background:
            "radial-gradient(circle at top left, rgba(209,123,73,0.16), transparent 28%), radial-gradient(circle at top right, rgba(11,79,108,0.14), transparent 24%), linear-gradient(180deg, #f7f3ec 0%, #efe5d8 100%)",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          border: `1px solid ${alpha("#0b4f6c", 0.08)}`,
          boxShadow: "0 24px 64px rgba(20, 36, 52, 0.08)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          paddingInline: 18,
        },
        containedPrimary: {
          boxShadow: "0 12px 28px rgba(11, 79, 108, 0.18)",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 600,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 20,
        },
      },
    },
  },
});
