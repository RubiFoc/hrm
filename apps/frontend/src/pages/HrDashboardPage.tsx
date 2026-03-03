import { Card, CardContent, Grid2, Typography } from "@mui/material";

const cards = [
  "Vacancies",
  "Pipeline",
  "Interview Calendar",
  "Shortlist Review",
];

export function HrDashboardPage() {
  return (
    <Grid2 container spacing={2}>
      {cards.map((item) => (
        <Grid2 size={{ xs: 12, sm: 6 }} key={item}>
          <Card>
            <CardContent>
              <Typography variant="h6">{item}</Typography>
              <Typography variant="body2">M1 placeholder for task implementation.</Typography>
            </CardContent>
          </Card>
        </Grid2>
      ))}
    </Grid2>
  );
}
