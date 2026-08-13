export function shortHash(hash: string | null | undefined, length = 12): string {
  if (!hash) return "";
  return hash.length <= length ? hash : hash.slice(0, length);
}

export function score3(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return value.toFixed(3);
}

export function seconds1(value: number): string {
  return `${value.toFixed(1)}s`;
}

/** Y/n flags for campaign runs: "YnY" reads as instability, never 67%. */
export function caughtFlags(caught: boolean[]): string {
  return caught.map((c) => (c ? "Y" : "n")).join(" ");
}
