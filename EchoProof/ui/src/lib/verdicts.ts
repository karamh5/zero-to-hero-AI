/** Verdict presentation metadata. The five states and no sixth.
 *
 * Verdict is never conveyed by color alone: every rendering carries the exact
 * verdict string (machine face) plus a position or shape. `reliability` exists
 * because conflicting_sections agreed 0/3 in blind labelling and the human
 * labeller never chose it in 25 items; the UI de-weights it visibly wherever
 * it appears.
 */

import type { Verdict } from "../types";
import { ABSTENTIONS } from "../types";

export interface VerdictMeta {
  verdict: Verdict;
  label: string;
  kind: "decision" | "abstention";
  cssVar: string;
  /** where the verdict sits relative to the retrieval thresholds */
  axis: "below_floor" | "band" | "above_ceiling" | "conflict" | "decided";
  meaning: string;
  deweighted?: boolean;
}

export const VERDICT_META: Record<Verdict, VerdictMeta> = {
  supported: {
    verdict: "supported",
    label: "supported",
    kind: "decision",
    cssVar: "--sig-supported",
    axis: "above_ceiling",
    meaning: "The retrieved rule supports what the agent said.",
  },
  contradicted: {
    verdict: "contradicted",
    label: "contradicted",
    kind: "decision",
    cssVar: "--sig-contradicted",
    axis: "above_ceiling",
    meaning: "The retrieved rule contradicts what the agent said.",
  },
  no_governing_rule: {
    verdict: "no_governing_rule",
    label: "no governing rule",
    kind: "abstention",
    cssVar: "--sig-abstain-ngr",
    axis: "below_floor",
    meaning:
      "Nothing in the corpus cleared the retrieval floor. The only abstention that feeds the policy gap list.",
  },
  retrieval_below_confidence: {
    verdict: "retrieval_below_confidence",
    label: "retrieval below confidence",
    kind: "abstention",
    cssVar: "--sig-abstain-rbc",
    axis: "band",
    meaning:
      "Something probably governs this, but retrieval was not confident enough to adjudicate. Routes to human review.",
  },
  conflicting_sections: {
    verdict: "conflicting_sections",
    label: "conflicting sections",
    kind: "abstention",
    cssVar: "--sig-abstain-cs",
    axis: "conflict",
    meaning:
      "Two plausible candidates point different ways. Routes to human review.",
    deweighted: true,
  },
};

export const DEWEIGHT_NOTE =
  "conflicting_sections agreed 0 of 3 in blind labelling and the human labeller never selected it across 25 items. Treat this state as the least reliable of the five.";

export function isAbstention(verdict: Verdict): boolean {
  return ABSTENTIONS.has(verdict);
}

export function verdictColor(verdict: Verdict): string {
  return `var(${VERDICT_META[verdict].cssVar})`;
}
