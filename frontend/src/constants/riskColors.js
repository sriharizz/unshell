export const NODE_COLORS = {
  AUTO_APPROVE: { bg: "#0F2318", border: "#5CB87A", pulse: false },
  MEDIUM_RISK:  { bg: "#2A1E08", border: "#E8A848", pulse: false },
  HIGH_RISK:    { bg: "#1E1535", border: "#8B7CE8", pulse: true  },
  CRITICAL:     { bg: "#2A0E0B", border: "#E06B5A", pulse: true  },
  OFFSHORE:     { bg: "#0A1E2E", border: "#4DB8C8", pulse: false },
  UNVERIFIED_AI:{ bg: "#1A1729", border: "#6E6B8A", pulse: false }
};

export const SCORE_THRESHOLDS = {
  AUTO_APPROVE: { max: 29,  label: "Auto-Approve", color: "green"   },
  HUMAN_REVIEW: { max: 64,  label: "Human Review", color: "amber"   },
  AUTO_REJECT:  { max: 94,  label: "Auto-Reject",  color: "red"     },
  CRITICAL:     { max: 100, label: "SAR Required",  color: "crimson" }
};

export const RISK_LEVEL_ORDER = ["AUTO_APPROVE", "MEDIUM_RISK", "HIGH_RISK", "CRITICAL"];

export function getRiskColor(riskLevel) {
  return NODE_COLORS[riskLevel] || NODE_COLORS.MEDIUM_RISK;
}

export function getScoreLabel(score) {
  if (score <= 29)  return SCORE_THRESHOLDS.AUTO_APPROVE;
  if (score <= 64)  return SCORE_THRESHOLDS.HUMAN_REVIEW;
  if (score <= 94)  return SCORE_THRESHOLDS.AUTO_REJECT;
  return SCORE_THRESHOLDS.CRITICAL;
}
