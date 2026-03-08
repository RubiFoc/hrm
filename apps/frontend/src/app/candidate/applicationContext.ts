export type CandidateApplicationContext = {
  vacancyId: string;
  vacancyTitle: string | null;
  candidateId: string;
  parsingJobId: string;
};

const CANDIDATE_APPLICATION_CONTEXT_KEY = "hrm_candidate_application_context";

/**
 * Read the latest candidate application tracking payload from session storage.
 */
export function readCandidateApplicationContext(): CandidateApplicationContext | null {
  const rawValue = window.sessionStorage.getItem(CANDIDATE_APPLICATION_CONTEXT_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as Partial<CandidateApplicationContext>;
    if (
      typeof parsed.vacancyId !== "string"
      || typeof parsed.candidateId !== "string"
      || typeof parsed.parsingJobId !== "string"
    ) {
      return null;
    }
    return {
      vacancyId: parsed.vacancyId,
      vacancyTitle: typeof parsed.vacancyTitle === "string" ? parsed.vacancyTitle : null,
      candidateId: parsed.candidateId,
      parsingJobId: parsed.parsingJobId,
    };
  } catch {
    return null;
  }
}

/**
 * Persist the latest candidate application tracking payload to session storage.
 */
export function writeCandidateApplicationContext(context: CandidateApplicationContext): void {
  window.sessionStorage.setItem(
    CANDIDATE_APPLICATION_CONTEXT_KEY,
    JSON.stringify(context),
  );
}

/**
 * Remove stored candidate application tracking payload from session storage.
 */
export function clearCandidateApplicationContext(): void {
  window.sessionStorage.removeItem(CANDIDATE_APPLICATION_CONTEXT_KEY);
}
