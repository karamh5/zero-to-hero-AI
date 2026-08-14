/** The Compliance Core: one object, many meaningful states.
 *
 * Built from EchoProof's own parts rather than from a generic shape. A ring
 * of policy sections encloses a smaller cluster of claim nodes, and retrieval
 * links draw between them while retrieval is happening. It is deliberately
 * not an orb, a microphone, a waveform or a reactor.
 *
 * The state machine is the point:
 *
 *   idle        the object is composed and nearly still
 *   submitted   it draws in, ready
 *   extracting  claim nodes light in the centre
 *   retrieving  links reach from the claim toward the policy ring
 *   judging     one section separates from the ring
 *   verdict     the selected section locks, tinted by the verdict
 *   sealed      the selected section locks and the field settles
 *
 * The critical rule from the rest of this product holds here: a state change
 * only ever happens because a real backend event arrived. Nothing in this
 * component advances on a timer, and there is no representation of progress
 * toward completion. Idle rotation is a stationary object being looked at,
 * not work being done, and it slows to almost nothing while the page is being
 * read.
 *
 * `amplitude` is the one continuous input, and it is only ever fed from real
 * decoded audio while a clip is playing. It is never synthesised.
 */

import { useEffect, useRef } from "react";
import * as THREE from "three";
import "./compliancecore.css";

export type CoreState =
  | "idle"
  | "submitted"
  | "extracting"
  | "retrieving"
  | "judging"
  | "verdict"
  | "sealed";

export type CoreTone = "neutral" | "supported" | "contradicted" | "abstain";

interface Props {
  state?: CoreState;
  tone?: CoreTone;
  /** number of provisions in the corpus; sets the ring's density */
  sections?: number;
  /** number of claims found in the turn; sets the inner cluster */
  claims?: number;
  /** 0..1 from real decoded audio, only while a clip plays */
  amplitude?: number;
  /** hero is large and slow, panel is compact, mini sits inside a row */
  scale?: "hero" | "panel" | "mini";
  className?: string;
}

/* Matched to the signal tokens on the graphite ground. Kept as literals
   because a WebGL material needs a number, and read once at construction
   would be the only alternative. */
const TONE_HEX: Record<CoreTone, number> = {
  neutral: 0x868c97,
  supported: 0x5bb295,
  contradicted: 0xe4705f,
  abstain: 0x8aa0bd,
};

/** Deterministic pseudo-random so the object is identical on every render. */
function seeded(seed: number): () => number {
  let value = seed >>> 0;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

export function ComplianceCore({
  state = "idle",
  tone = "neutral",
  sections = 303,
  claims = 4,
  amplitude = 0,
  scale = "hero",
  className = "",
}: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef<{
    setState: (s: CoreState, t: CoreTone) => void;
    setAmplitude: (a: number) => void;
  } | null>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const width = mount.clientWidth || 1;
    const height = mount.clientHeight || 1;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "low-power",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);
    camera.position.set(0, 0.6, 7.2);
    camera.lookAt(0, 0, 0);

    const group = new THREE.Group();
    scene.add(group);

    const readVar = (name: string, fallback: string) =>
      getComputedStyle(mount).getPropertyValue(name).trim() || fallback;
    const inkHex = new THREE.Color(readVar("--ink", "#e9e7e1")).getHex();
    const faintHex = new THREE.Color(readVar("--ink-faint", "#868c97")).getHex();
    const traceHex = new THREE.Color(readVar("--sig-trace", "#45c8da")).getHex();

    // ---- the policy ring: one mark per provision, capped for frame budget
    const ringCount = Math.min(sections, 320);
    const ringGeometry = new THREE.BufferGeometry();
    const ringPositions = new Float32Array(ringCount * 3);
    const random = seeded(sections * 7919 + 13);
    const ringRadius = 2.55;
    for (let index = 0; index < ringCount; index += 1) {
      const angle = (index / ringCount) * Math.PI * 2;
      const wobble = (random() - 0.5) * 0.16;
      const lift = (random() - 0.5) * 0.5;
      ringPositions[index * 3] = Math.cos(angle) * (ringRadius + wobble);
      ringPositions[index * 3 + 1] = lift;
      ringPositions[index * 3 + 2] = Math.sin(angle) * (ringRadius + wobble);
    }
    ringGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(ringPositions, 3),
    );
    const ringMaterial = new THREE.PointsMaterial({
      color: faintHex,
      size: 0.055,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.85,
    });
    const ring = new THREE.Points(ringGeometry, ringMaterial);
    group.add(ring);

    // ---- the claim cluster: low-poly fragments at seeded positions
    const claimCount = Math.max(3, Math.min(claims, 12));
    const fragments: THREE.Mesh[] = [];
    const fragmentGeometry = new THREE.IcosahedronGeometry(0.17, 0);
    for (let index = 0; index < claimCount; index += 1) {
      const material = new THREE.MeshBasicMaterial({
        color: inkHex,
        wireframe: true,
        transparent: true,
        opacity: 0.55,
      });
      const mesh = new THREE.Mesh(fragmentGeometry, material);
      const angle = (index / claimCount) * Math.PI * 2;
      const radius = 0.55 + random() * 0.35;
      mesh.position.set(
        Math.cos(angle) * radius,
        (random() - 0.5) * 0.7,
        Math.sin(angle) * radius,
      );
      mesh.userData.base = mesh.position.clone();
      mesh.userData.spin = 0.002 + random() * 0.004;
      group.add(mesh);
      fragments.push(mesh);
    }

    // ---- the selected section: separates from the ring when judging lands
    const selected = new THREE.Mesh(
      new THREE.TetrahedronGeometry(0.3, 0),
      new THREE.MeshBasicMaterial({
        color: TONE_HEX[tone],
        wireframe: false,
        transparent: true,
        opacity: 0,
      }),
    );
    selected.position.set(0, 1.55, 0);
    group.add(selected);

    // ---- retrieval links: claim centre out toward the ring
    const linkCount = 14;
    const linkPositions = new Float32Array(linkCount * 2 * 3);
    for (let index = 0; index < linkCount; index += 1) {
      const angle = (index / linkCount) * Math.PI * 2 + 0.2;
      linkPositions[index * 6] = 0;
      linkPositions[index * 6 + 1] = 0;
      linkPositions[index * 6 + 2] = 0;
      linkPositions[index * 6 + 3] = Math.cos(angle) * ringRadius;
      linkPositions[index * 6 + 4] = 0;
      linkPositions[index * 6 + 5] = Math.sin(angle) * ringRadius;
    }
    const linkGeometry = new THREE.BufferGeometry();
    linkGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(linkPositions, 3),
    );
    const linkMaterial = new THREE.LineBasicMaterial({
      color: traceHex,
      transparent: true,
      opacity: 0,
    });
    const links = new THREE.LineSegments(linkGeometry, linkMaterial);
    group.add(links);

    // ---- state, driven only from outside
    let currentState: CoreState = state;
    let currentTone: CoreTone = tone;
    let amp = 0;
    let ampTarget = 0;
    // Every state change stamps this, so easing runs from the moment the
    // event arrived rather than from a clock of its own.
    let changedAt = performance.now();

    const pointer = { x: 0, y: 0 };
    const onPointer = (event: PointerEvent) => {
      const rect = mount.getBoundingClientRect();
      pointer.x = (event.clientX - rect.left) / rect.width - 0.5;
      pointer.y = (event.clientY - rect.top) / rect.height - 0.5;
    };
    window.addEventListener("pointermove", onPointer, { passive: true });

    apiRef.current = {
      setState: (next, nextTone) => {
        if (next !== currentState || nextTone !== currentTone) {
          currentState = next;
          currentTone = nextTone;
          changedAt = performance.now();
          (selected.material as THREE.MeshBasicMaterial).color.setHex(
            TONE_HEX[nextTone],
          );
        }
      },
      setAmplitude: (value) => {
        ampTarget = Math.max(0, Math.min(1, value));
      },
    };

    let frame = 0;
    let rotation = 0;
    const targetRotation = { x: 0, y: 0 };

    const render = () => {
      const since = (performance.now() - changedAt) / 1000;
      // Arrival easing on every state change: fast in, then settle.
      const arrive = Math.min(1, 1 - Math.pow(1 - Math.min(since / 0.42, 1), 3));

      // Idle rotation is slow and gets slower once the object has been sitting
      // for a while, so a page being read is not competing with motion.
      if (!still) {
        const restless = currentState === "idle" ? Math.max(0.25, 1 - since / 14) : 1;
        rotation += 0.00055 * restless;
      }

      targetRotation.y = pointer.x * 0.16;
      targetRotation.x = pointer.y * 0.12;
      group.rotation.y += (rotation + targetRotation.y - group.rotation.y) * 0.06;
      group.rotation.x += (targetRotation.x - group.rotation.x) * 0.06;

      amp += (ampTarget - amp) * 0.25;

      // Ring: breathes very slightly with real audio amplitude only.
      const ringScale = 1 + amp * 0.06;
      ring.scale.setScalar(ringScale);
      ringMaterial.opacity = 0.6 + amp * 0.35;

      // Claim fragments.
      const lit =
        currentState === "extracting" ||
        currentState === "retrieving" ||
        currentState === "judging" ||
        currentState === "verdict" ||
        currentState === "sealed";
      fragments.forEach((mesh, index) => {
        mesh.rotation.x += mesh.userData.spin;
        mesh.rotation.y += mesh.userData.spin * 0.7;
        const base = mesh.userData.base as THREE.Vector3;
        const spread = currentState === "idle" ? 1 : 1.16;
        const bump = amp * 0.14 * Math.sin(index * 1.7);
        mesh.position.lerp(
          new THREE.Vector3(
            base.x * spread,
            base.y * spread + bump,
            base.z * spread,
          ),
          0.08,
        );
        const material = mesh.material as THREE.MeshBasicMaterial;
        const want = lit ? 0.95 : 0.5;
        material.opacity += (want - material.opacity) * 0.08;
      });

      // Retrieval links appear only while retrieval is actually running.
      const linkWant = currentState === "retrieving" ? 0.5 * arrive : 0;
      linkMaterial.opacity += (linkWant - linkMaterial.opacity) * 0.12;
      links.rotation.y += currentState === "retrieving" ? 0.004 : 0;

      // The selected section separates once the judge has ruled.
      const decided =
        currentState === "judging" ||
        currentState === "verdict" ||
        currentState === "sealed";
      const selectedMaterial = selected.material as THREE.MeshBasicMaterial;
      const selectedWant = decided ? (currentState === "judging" ? 0.4 : 0.95) : 0;
      selectedMaterial.opacity += (selectedWant - selectedMaterial.opacity) * 0.1;
      selected.rotation.y += decided ? 0.006 : 0.001;
      selected.position.y += (
        (decided ? 1.75 : 1.55) - selected.position.y
      ) * 0.06;

      renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);
    // One synchronous frame so the object exists even where rAF never fires.
    renderer.render(scene, camera);

    const resize = () => {
      const w = mount.clientWidth || 1;
      const h = mount.clientHeight || 1;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("pointermove", onPointer);
      apiRef.current = null;
      ringGeometry.dispose();
      fragmentGeometry.dispose();
      linkGeometry.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
    // Rebuilt only when the corpus shape changes, never on state changes:
    // those go through the imperative api so the scene is never torn down
    // mid-adjudication.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sections, claims, scale]);

  useEffect(() => {
    apiRef.current?.setState(state, tone);
  }, [state, tone]);

  useEffect(() => {
    apiRef.current?.setAmplitude(amplitude);
  }, [amplitude]);

  return <div ref={mountRef} className={`core core-${scale} ${className}`} />;
}
