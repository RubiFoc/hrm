import { Box, Chip, Paper, Stack, Typography } from "@mui/material";

type PublicRailCardItem = {
  description: string;
  title: string;
};

type PublicRailCardProps = {
  chips?: string[];
  eyebrow: string;
  footnote?: string;
  items: PublicRailCardItem[];
  subtitle: string;
  title: string;
};

/**
 * Shared side-rail card for public-facing pages.
 *
 * The card summarizes the current page with a short narrative, a few chips, and three concise
 * steps or facts so public pages feel structured without adding more route complexity.
 */
export function PublicRailCard({
  chips = [],
  eyebrow,
  footnote,
  items,
  subtitle,
  title,
}: PublicRailCardProps) {
  return (
    <Paper
      sx={{
        overflow: "hidden",
        position: "relative",
        p: 2.5,
        height: "100%",
        color: "primary.contrastText",
        background:
          "linear-gradient(135deg, rgba(11,79,108,0.96) 0%, rgba(31,100,88,0.94) 100%)",
      }}
    >
      <Box
        sx={{
          position: "absolute",
          top: -100,
          right: -70,
          width: 220,
          height: 220,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(247,242,234,0.18), transparent 70%)",
        }}
      />
      <Stack spacing={1.75} sx={{ position: "relative", zIndex: 1 }}>
        <Typography
          variant="overline"
          sx={{
            color: "secondary.light",
            fontWeight: 700,
            letterSpacing: "0.22em",
          }}
        >
          {eyebrow}
        </Typography>

        <Typography variant="h5" color="inherit">
          {title}
        </Typography>

        <Typography variant="body2" sx={{ color: "rgba(247, 242, 234, 0.84)" }}>
          {subtitle}
        </Typography>

        {chips.length > 0 ? (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {chips.map((chip) => (
              <Chip
                key={chip}
                label={chip}
                color="secondary"
                size="small"
                variant="filled"
              />
            ))}
          </Stack>
        ) : null}

        <Stack spacing={1.25}>
          {items.map((item, index) => (
            <Stack
              key={`${item.title}-${index}`}
              spacing={0.75}
              sx={{
                p: 1.5,
                borderRadius: 3,
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.14)",
              }}
            >
              <Stack direction="row" spacing={1.25} alignItems="flex-start">
                <Chip
                  label={String(index + 1).padStart(2, "0")}
                  size="small"
                  color="secondary"
                  sx={{ minWidth: 46 }}
                />
                <Stack spacing={0.25}>
                  <Typography variant="subtitle2" color="inherit">
                    {item.title}
                  </Typography>
                  <Typography variant="body2" sx={{ color: "rgba(247, 242, 234, 0.78)" }}>
                    {item.description}
                  </Typography>
                </Stack>
              </Stack>
            </Stack>
          ))}
        </Stack>

        {footnote ? (
          <Typography variant="caption" sx={{ color: "rgba(247, 242, 234, 0.68)" }}>
            {footnote}
          </Typography>
        ) : null}
      </Stack>
    </Paper>
  );
}
