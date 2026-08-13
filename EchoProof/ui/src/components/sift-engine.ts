/** The sift engine: a canvas rendering of the corpus being sifted.
 *
 * The corpus is a field of marks, one per provision, grouped into columns by
 * root section; both the count and the grouping are read from the pack. To
 * the right stands a vertical score axis crossed by the floor and ceiling
 * read from the run's recorded thresholds. Position on that axis IS the
 * verdict: below the floor is no_governing_rule, the band is
 * retrieval_below_confidence, above the ceiling proceeds to the judge.
 *
 * Honesty constraints, enforced structurally:
 *  - Every animation is triggered by a real pipeline event and settles; there
 *    is no idle motion. When the backend is silently working, the field is
 *    still, and the only moving thing is the elapsed clock in the DOM.
 *  - Live events carry the candidate COUNT and the TOP score, not fifty
 *    scores, so lifted candidates land in a neutral ranked pool, never at
 *    invented positions on the axis. Only the top candidate, whose score the
 *    event genuinely carries, lands on the scale. The full recorded
 *    distribution is drawn only once the evidence log exists to supply it.
 *  - A deterministic decision draws the short path and never touches the
 *    field, because retrieval genuinely never ran.
 *
 * Under prefers-reduced-motion every transition renders its end state
 * immediately; the same information, no tweens.
 */

export interface SiftSection {
  section_id: string;
  root: string;
}

export interface SiftThresholds {
  floor: number;
  ceiling: number;
}

interface Mark {
  x: number;
  y: number;
  section_id: string;
}

interface Tween {
  start: number;
  duration: number;
  draw: (t: number) => void;
  done?: () => void;
}

interface AxisDot {
  score: number;
  label: string;
  kind: "top" | "record" | "selected";
}

const FIELD_RIGHT = 0.56; // fraction of width given to the field
const AXIS_X = 0.72; // axis line position as fraction of width

export class SiftEngine {
  private g: CanvasRenderingContext2D;
  private width = 0;
  private height = 0;
  private dpr = 1;
  private marks: Mark[] = [];
  private byId = new Map<string, Mark>();
  private roots: { root: string; x: number }[] = [];
  private thresholds: SiftThresholds | null = null;
  private tweens: Tween[] = [];
  private raf = 0;

  private poolCount = 0;
  private poolLabel = "";
  private axisDots: AxisDot[] = [];
  private selected: { section_id: string; color: string; label: string } | null =
    null;
  private deterministicPath = false;
  private activeQuery = false;
  private canvas: HTMLCanvasElement;
  private reducedMotion: boolean;

  constructor(canvas: HTMLCanvasElement, reducedMotion: boolean) {
    this.canvas = canvas;
    this.reducedMotion = reducedMotion;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("canvas 2d context unavailable");
    this.g = context;
    this.resize();
  }

  resize(): void {
    this.dpr = window.devicePixelRatio || 1;
    this.width = this.canvas.clientWidth;
    this.height = this.canvas.clientHeight;
    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.g.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    this.layoutField();
    this.draw();
  }

  setCorpus(sections: SiftSection[]): void {
    this.marks = sections.map((s) => ({ x: 0, y: 0, section_id: s.section_id }));
    this.byId = new Map(this.marks.map((m) => [m.section_id, m]));
    const rootsInOrder: string[] = [];
    for (const section of sections) {
      if (!rootsInOrder.includes(section.root)) rootsInOrder.push(section.root);
    }
    this.roots = rootsInOrder.map((root) => ({ root, x: 0 }));
    this.sectionRoots = new Map(sections.map((s) => [s.section_id, s.root]));
    this.layoutField();
    this.draw();
  }

  private sectionRoots = new Map<string, string>();

  setThresholds(thresholds: SiftThresholds): void {
    this.thresholds = thresholds;
    this.draw();
  }

  /** Reset per-claim state. The field itself persists between claims. */
  beginClaim(): void {
    this.poolCount = 0;
    this.poolLabel = "";
    this.axisDots = [];
    this.selected = null;
    this.deterministicPath = false;
    this.activeQuery = false;
    this.draw();
  }

  /** A query fired into the field. One-shot ripple; then held in-flight. */
  query(): void {
    this.activeQuery = true;
    if (this.reducedMotion) {
      this.draw();
      return;
    }
    const origin = {
      x: this.width * FIELD_RIGHT * 0.5,
      y: this.height * 0.5,
    };
    this.addTween(650, (t) => {
      this.draw();
      const radius = t * this.width * FIELD_RIGHT * 0.65;
      this.g.strokeStyle = this.cssVar("--sig-trace");
      this.g.globalAlpha = (1 - t) * 0.8;
      this.g.beginPath();
      this.g.arc(origin.x, origin.y, radius, 0, Math.PI * 2);
      this.g.stroke();
      this.g.globalAlpha = 1;
    });
  }

  /** Candidates ranked: `count` marks lift into the ranked pool, and the top
   * candidate, whose score the event carries, lands on the axis. */
  ranked(count: number, topSection: string | null, topScore: number | null): void {
    this.activeQuery = false;
    const finish = () => {
      this.poolCount = count;
      this.poolLabel = `${count} candidates ranked`;
      if (topSection !== null && topScore !== null) {
        this.axisDots = this.axisDots.filter((d) => d.kind !== "top");
        this.axisDots.push({ score: topScore, label: topSection, kind: "top" });
      }
      this.draw();
    };
    if (this.reducedMotion) {
      finish();
      return;
    }
    const sample = this.marks.length
      ? Array.from({ length: Math.min(count, 50) }, () =>
          this.marks[Math.floor(Math.random() * this.marks.length)],
        )
      : [];
    const pool = this.poolBox();
    this.addTween(
      700,
      (t) => {
        this.draw();
        const ease = 1 - (1 - t) * (1 - t);
        this.g.fillStyle = this.cssVar("--sig-trace");
        for (let index = 0; index < sample.length; index += 1) {
          const from = sample[index];
          const tx = pool.x + (index % 10) * 6 + 3;
          const ty = pool.y + Math.floor(index / 10) * 6 + 3;
          const x = from.x + (tx - from.x) * ease;
          const y = from.y + (ty - from.y) * ease;
          this.g.globalAlpha = 0.7;
          this.g.fillRect(x - 1.5, y - 1.5, 3, 3);
        }
        this.g.globalAlpha = 1;
      },
      finish,
    );
  }

  /** The shortlist offered to the judge. */
  shortlist(count: number): void {
    this.poolLabel = `${count} sections offered to the judge`;
    this.draw();
  }

  /** The settling: the judge's selected section lifts out of the field. */
  settle(sectionId: string | null, color: string, verdictLabel: string): void {
    const finish = () => {
      this.selected = sectionId
        ? { section_id: sectionId, color, label: verdictLabel }
        : null;
      this.draw();
    };
    if (this.reducedMotion || !sectionId || !this.byId.has(sectionId)) {
      finish();
      return;
    }
    const mark = this.byId.get(sectionId)!;
    const target = this.selectedSlot();
    this.addTween(
      520,
      (t) => {
        this.draw();
        const ease = 1 - Math.pow(1 - t, 3);
        const x = mark.x + (target.x - mark.x) * ease;
        const y = mark.y + (target.y - mark.y) * ease;
        this.g.fillStyle = color;
        this.g.fillRect(x - 3, y - 3, 6, 6);
      },
      finish,
    );
  }

  /** Deterministic short-circuit: the field never activates. */
  deterministic(): void {
    this.deterministicPath = true;
    this.draw();
  }

  /** The recorded candidate distribution, once the evidence log exists. */
  backfill(candidates: { section_id: string; score: number }[], selectedScore: number | null): void {
    this.axisDots = this.axisDots.filter((d) => d.kind === "top");
    const seen = new Set<string>();
    for (const candidate of candidates) {
      if (seen.has(candidate.section_id)) continue;
      seen.add(candidate.section_id);
      this.axisDots.push({
        score: candidate.score,
        label: candidate.section_id,
        kind: "record",
      });
    }
    if (selectedScore !== null) {
      this.axisDots.push({ score: selectedScore, label: "", kind: "selected" });
    }
    this.draw();
  }

  destroy(): void {
    cancelAnimationFrame(this.raf);
  }

  // -- geometry ----------------------------------------------------------

  private layoutField(): void {
    if (!this.marks.length || !this.width) return;
    const fieldWidth = this.width * FIELD_RIGHT;
    const top = 26;
    const bottom = this.height - 34;
    const columns = this.roots.length || 1;
    const columnWidth = fieldWidth / columns;

    const byRoot = new Map<string, Mark[]>();
    for (const mark of this.marks) {
      const root = this.sectionRoots.get(mark.section_id) ?? "";
      if (!byRoot.has(root)) byRoot.set(root, []);
      byRoot.get(root)!.push(mark);
    }

    this.roots.forEach((entry, columnIndex) => {
      const members = byRoot.get(entry.root) ?? [];
      entry.x = columnIndex * columnWidth + columnWidth / 2;
      const perColumn = Math.max(
        1,
        Math.floor((bottom - top) / 9),
      );
      members.forEach((mark, index) => {
        const col = Math.floor(index / perColumn);
        const row = index % perColumn;
        mark.x = entry.x - 6 + col * 7 - (Math.ceil(members.length / perColumn) - 1) * 3;
        mark.y = top + row * 9;
      });
    });
  }

  private axisTop(): number {
    return 26;
  }

  private axisBottom(): number {
    return this.height - 34;
  }

  private scoreY(score: number): number {
    const clamped = Math.max(0, Math.min(1, score));
    return this.axisTop() + (1 - clamped) * (this.axisBottom() - this.axisTop());
  }

  private poolBox(): { x: number; y: number; w: number; h: number } {
    return {
      x: this.width * (FIELD_RIGHT + 0.02),
      y: this.height * 0.36,
      w: 62,
      h: 34,
    };
  }

  private selectedSlot(): { x: number; y: number } {
    return { x: this.width * 0.92, y: this.height * 0.16 };
  }

  // -- drawing -----------------------------------------------------------

  private cssVar(name: string): string {
    return getComputedStyle(this.canvas).getPropertyValue(name).trim() || "#888";
  }

  draw(): void {
    const { g } = this;
    g.clearRect(0, 0, this.width, this.height);
    if (!this.width) return;

    const inkFaint = this.cssVar("--ink-faint");
    const inkMuted = this.cssVar("--ink-muted");
    const ink = this.cssVar("--ink");
    const line = this.cssVar("--line-strong");
    const trace = this.cssVar("--sig-trace");

    // field
    g.fillStyle = this.deterministicPath ? this.cssVar("--line") : inkFaint;
    for (const mark of this.marks) {
      g.fillRect(mark.x - 1.25, mark.y - 1.25, 2.5, 2.5);
    }
    // root labels
    g.font = "9px IBM Plex Mono, monospace";
    g.fillStyle = inkMuted;
    g.textAlign = "center";
    for (const entry of this.roots) {
      const label =
        entry.root.length > 9 ? `${entry.root.slice(0, 8)}…` : entry.root;
      g.save();
      g.translate(entry.x, this.height - 20);
      g.fillText(label, 0, 0);
      g.restore();
    }

    // active query glow along the field baseline: real in-flight state
    if (this.activeQuery) {
      g.fillStyle = trace;
      g.fillRect(0, this.height - 31, this.width * FIELD_RIGHT, 2);
    }

    // axis
    const axisX = this.width * AXIS_X;
    g.strokeStyle = line;
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(axisX, this.axisTop());
    g.lineTo(axisX, this.axisBottom());
    g.stroke();
    g.textAlign = "left";
    g.fillStyle = inkFaint;
    for (const tick of [0, 0.5, 1]) {
      const y = this.scoreY(tick);
      g.fillRect(axisX - 3, y, 6, 1);
      g.fillText(tick.toFixed(1), axisX - 26, y + 3);
    }

    // thresholds
    if (this.thresholds) {
      const { floor, ceiling } = this.thresholds;
      g.strokeStyle = ink;
      g.lineWidth = 1.4;
      const ceilingY = this.scoreY(ceiling);
      g.beginPath();
      g.moveTo(axisX - 8, ceilingY);
      g.lineTo(this.width - 8, ceilingY);
      g.stroke();
      g.setLineDash([5, 4]);
      const floorY = this.scoreY(floor);
      g.beginPath();
      g.moveTo(axisX - 8, floorY);
      g.lineTo(this.width - 8, floorY);
      g.stroke();
      g.setLineDash([]);
      g.fillStyle = inkMuted;
      g.fillText(`ceiling ${ceiling.toFixed(3)}`, axisX + 8, ceilingY - 5);
      g.fillText(`floor ${floor.toFixed(3)}`, axisX + 8, floorY + 12);
      g.fillStyle = inkFaint;
      g.fillText("to the judge", axisX + 8, this.axisTop() + 10);
      g.fillText("below confidence", axisX + 8, (ceilingY + floorY) / 2 + 3);
      g.fillText("no governing rule", axisX + 8, (floorY + this.axisBottom()) / 2 + 3);
    }

    // ranked pool
    if (this.poolCount > 0) {
      const pool = this.poolBox();
      g.strokeStyle = line;
      g.strokeRect(pool.x, pool.y, pool.w, pool.h);
      g.fillStyle = inkMuted;
      const dots = Math.min(this.poolCount, 50);
      for (let index = 0; index < dots; index += 1) {
        g.fillRect(pool.x + (index % 10) * 6 + 3, pool.y + Math.floor(index / 10) * 6 + 3, 3, 3);
      }
      g.fillText(this.poolLabel, pool.x, pool.y + pool.h + 12);
    }

    // axis dots
    for (const dot of this.axisDots) {
      const y = this.scoreY(dot.score);
      if (dot.kind === "selected") {
        g.strokeStyle = ink;
        g.lineWidth = 2;
        g.beginPath();
        g.moveTo(axisX - 7, y);
        g.lineTo(axisX + 7, y);
        g.stroke();
        continue;
      }
      g.fillStyle = dot.kind === "top" ? trace : inkMuted;
      g.beginPath();
      g.arc(axisX, y, dot.kind === "top" ? 4 : 2.4, 0, Math.PI * 2);
      g.fill();
      if (dot.kind === "top") {
        g.fillStyle = ink;
        g.fillText(`${dot.label}  ${dot.score.toFixed(3)}`, axisX + 10, y + 3);
      }
    }

    // deterministic short path
    if (this.deterministicPath) {
      const slot = this.selectedSlot();
      g.strokeStyle = this.cssVar("--sig-deterministic");
      g.lineWidth = 1.6;
      g.beginPath();
      g.moveTo(12, 14);
      g.lineTo(slot.x - 14, slot.y);
      g.stroke();
      g.fillStyle = this.cssVar("--sig-deterministic");
      g.textAlign = "left";
      g.fillText("decided in code: retrieval never ran", 12, 10);
    }

    // selected section
    if (this.selected) {
      const slot = this.selectedSlot();
      g.fillStyle = this.selected.color;
      g.fillRect(slot.x - 4, slot.y - 4, 8, 8);
      g.textAlign = "right";
      g.fillStyle = ink;
      g.fillText(this.selected.section_id, slot.x - 10, slot.y + 3);
      g.fillStyle = this.selected.color;
      g.fillText(this.selected.label, slot.x - 10, slot.y + 16);
      g.textAlign = "left";
      // tether back to its field position: the provision came from somewhere
      const mark = this.byId.get(this.selected.section_id);
      if (mark) {
        g.strokeStyle = this.selected.color;
        g.globalAlpha = 0.45;
        g.lineWidth = 1;
        g.beginPath();
        g.moveTo(mark.x, mark.y);
        g.lineTo(slot.x - 6, slot.y);
        g.stroke();
        g.globalAlpha = 1;
        g.fillRect(mark.x - 2, mark.y - 2, 4, 4);
      }
    }
  }

  // -- animation plumbing ------------------------------------------------

  private addTween(duration: number, draw: (t: number) => void, done?: () => void): void {
    this.tweens.push({ start: performance.now(), duration, draw, done });
    if (!this.raf) this.loop();
  }

  private loop = (): void => {
    this.raf = requestAnimationFrame(() => {
      const now = performance.now();
      const remaining: Tween[] = [];
      let drewSomething = false;
      for (const tween of this.tweens) {
        const t = Math.min(1, (now - tween.start) / tween.duration);
        tween.draw(t);
        drewSomething = true;
        if (t >= 1) tween.done?.();
        else remaining.push(tween);
      }
      this.tweens = remaining;
      if (this.tweens.length) {
        this.loop();
      } else {
        this.raf = 0;
        if (drewSomething) this.draw();
      }
    });
  };
}
