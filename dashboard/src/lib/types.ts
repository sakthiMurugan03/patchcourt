export type Evidence = {
  tier: number;
  text: string;
};

export type Claim = {
  agent: string;
  issue: string;
  file: string;
  line: number;
  severity: number;
  evidence: Evidence[];
  confidence: number;
  tier: number;
  corroborated: boolean;
  source: "tool" | "llm";
};

export type FileReport = {
  file: string;
  claims: Claim[];
  score: number;
};

export type Debate = {
  file: string;
  issue: string;
  supporting: string;
  opposing: string;
  rounds: number;
};

export type Verdict = "MERGE" | "NEEDS_REVIEW" | "BLOCK";

export type Report = {
  pr_url: string;
  overall_score: number;
  verdict: Verdict;
  files: FileReport[];
  claims: Claim[];
  debate_transcripts: Debate[];
};

export const VERDICT_META = {
  MERGE: { label: "MERGE", color: "#2dd4bf", blurb: "No material risk found" },
  NEEDS_REVIEW: { label: "NEEDS REVIEW", color: "#fbbf24", blurb: "Low-confidence concerns remain" },
  BLOCK: { label: "BLOCK", color: "#f87171", blurb: "Evidence-backed issues must be fixed" },
} as const;

export const AGENT_META: Record<string, { color: string; name: string }> = {
  security: { color: "#f87171", name: "Security" },
  quality: { color: "#2dd4bf", name: "Quality" },
  pragmatist: { color: "#fbbf24", name: "Pragmatist" },
  tools: { color: "#818cf8", name: "Static Analysis" },
};

export const TIER_INFO: Record<number, { name: string; weight: number; blurb: string }> = {
  1: { name: "T1 — Tool Flag", weight: 1.0, blurb: "Direct static-analysis finding on file:line" },
  2: { name: "T2 — Corroborated", weight: 0.8, blurb: "Two tools agree on the same line" },
  3: { name: "T3 — Repo Policy", weight: 0.5, blurb: "Retrieved from repository policy/standards" },
  4: { name: "T4 — Git Precedent", weight: 0.4, blurb: "Pattern from history / similar past PRs" },
  5: { name: "T5 — LLM Assertion", weight: 0.1, blurb: "Model reasoning, never blocks alone" },
};

export type SonarSeverity = "BLOCKER" | "CRITICAL" | "MAJOR" | "MINOR" | "INFO";

export type SonarIssue = {
  file: string;
  line: number;
  severity: SonarSeverity;
  type: "VULNERABILITY" | "BUG" | "CODE_SMELL";
  rule: string;
  message: string;
  in_pr: boolean;
  suggested_tier: number;
};

export type SonarSummary = {
  vulnerabilities: number;
  bugs: number;
  code_smells: number;
};

export type BaselineComparison = {
  verdict: Verdict;
  overall_score: number;
  counts: {
    raw: number;
    confirmed: number;
    suppressed: number;
    sonar_missed: number;
  };
  confirmed: SonarIssue[];
  down_tiered: SonarIssue[];
  sonar_missed: Array<{
    file: string;
    line: number;
    severity: number;
    agent: string;
    tier: number;
    issue: string;
  }>;
};

export type BaselineReport = {
  generated_at: string;
  pr_url: string;
  component: string;
  server_url: string;
  total_open_issues: number;
  issues_touching_pr: number;
  summary: SonarSummary;
  issues: SonarIssue[];
  patchcourt?: {
    verdict: Verdict;
    overall_score: number;
    comparison: BaselineComparison;
  };
};