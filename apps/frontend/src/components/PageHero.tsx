import { type ReactNode } from "react";
import {
  alpha,
  Box,
  Button,
  Chip,
  Grid2,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

type HeroAction = {
  href: string;
  label: string;
  variant?: "contained" | "outlined" | "text";
};

type PageHeroProps = {
  actions?: HeroAction[];
  caption?: string;
  chips?: string[];
  description: string;
  eyebrow?: string;
  imageAlt?: string;
  imageSrc?: string;
  sideContent?: ReactNode;
  title: string;
};

/**
 * Shared marketing-style hero used across the landing, careers, and role pages.
 */
export function PageHero({
  actions = [],
  caption,
  chips = [],
  description,
  eyebrow,
  imageAlt,
  imageSrc,
  sideContent,
  title,
}: PageHeroProps) {
  return (
    <Paper
      sx={{
        overflow: "hidden",
        position: "relative",
        p: { xs: 3, md: 4 },
        background:
          "linear-gradient(135deg, rgba(255, 252, 247, 0.98) 0%, rgba(246, 238, 226, 0.98) 55%, rgba(229, 240, 244, 0.98) 100%)",
      }}
    >
      <Box
        sx={{
          position: "absolute",
          top: -120,
          right: -80,
          width: 260,
          height: 260,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(11,79,108,0.18), transparent 70%)",
        }}
      />
      <Grid2 container spacing={{ xs: 3, md: 4 }} alignItems="center">
        <Grid2 size={{ xs: 12, lg: imageSrc || sideContent ? 7 : 12 }}>
          <Stack spacing={2.5}>
            {eyebrow ? (
              <Typography
                variant="overline"
                sx={{
                  color: "secondary.main",
                  fontWeight: 700,
                  letterSpacing: "0.22em",
                }}
              >
                {eyebrow}
              </Typography>
            ) : null}

            <Typography variant="h2" sx={{ maxWidth: 760, fontSize: { xs: "2.4rem", md: "3.5rem" } }}>
              {title}
            </Typography>

            <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 680, fontSize: "1.05rem" }}>
              {description}
            </Typography>

            {chips.length > 0 ? (
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {chips.map((chip) => (
                  <Chip key={chip} label={chip} color="primary" variant="outlined" />
                ))}
              </Stack>
            ) : null}

            {actions.length > 0 ? (
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                {actions.map((action) => (
                  <Button
                    key={`${action.href}-${action.label}`}
                    component={RouterLink}
                    to={action.href}
                    variant={action.variant ?? "contained"}
                  >
                    {action.label}
                  </Button>
                ))}
              </Stack>
            ) : null}

            {caption ? (
              <Typography variant="caption" color="text.secondary">
                {caption}
              </Typography>
            ) : null}
          </Stack>
        </Grid2>

        {imageSrc || sideContent ? (
          <Grid2 size={{ xs: 12, lg: 5 }}>
            {imageSrc ? (
              <Box
                component="img"
                src={imageSrc}
                alt={imageAlt ?? title}
                sx={{
                  width: "100%",
                  minHeight: { xs: 260, md: 340 },
                  objectFit: "cover",
                  borderRadius: 5,
                  boxShadow: `0 28px 60px ${alpha("#142434", 0.22)}`,
                }}
              />
            ) : null}
            {sideContent ? <Box sx={{ mt: imageSrc ? 2 : 0 }}>{sideContent}</Box> : null}
          </Grid2>
        ) : null}
      </Grid2>
    </Paper>
  );
}
