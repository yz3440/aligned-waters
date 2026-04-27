import * as THREE from "three";
import { Pane } from "tweakpane";
import { loadManifest, splitPools, type ImageRecord } from "./data";
import { createRenderer, createCamera, createBackground } from "./scene";
import { Strand } from "./strand";
import {
  CANVAS_HEIGHT,
  DRAW_ORDER,
  type StrandConfig,
} from "./config";

const params = {
  strandCount: 23,
  scaleFactor: 1.0,
  gap: -50,
  stripWidthBase: 200,
  speed: 3.0,
};

async function init() {
  const allImages = await loadManifest();

  const scene = new THREE.Scene();
  const camera = createCamera();
  const renderer = createRenderer();

  createBackground(scene);

  let strands: Strand[] = [];

  function generateConfigs(): StrandConfig[] {
    const n = params.strandCount;
    const mid = Math.floor(n / 2);
    const configs: StrandConfig[] = [];

    for (let i = 0; i < n; i++) {
      const dist = Math.abs(i - mid) / Math.max(mid, 1); // 0 at center, 1 at edges
      const t = 1 - dist; // 1 at center, 0 at edges

      // Center is largest, edges smallest
      const height = (80 + 140 * t) * params.scaleFactor;
      const stripWidth = (params.stripWidthBase * (0.5 + 0.5 * t)) * params.scaleFactor;

      // Vary scroll cycles: edges faster, center slower
      const scrollCycles = dist < 0.3 ? 1 : dist < 0.6 ? 2 : 3;

      configs.push({ stripWidth, height, scrollCycles });
    }
    return configs;
  }

  function generateDrawOrder(n: number): number[] {
    // Edges first, center last
    const order: number[] = [];
    const mid = Math.floor(n / 2);
    for (let d = mid; d >= 0; d--) {
      if (mid - d >= 0 && mid - d < n) order.push(mid - d === mid ? -1 : mid - d);
      if (mid + d < n && d > 0) order.push(mid + d);
    }
    // Add center last
    const idx = order.indexOf(-1);
    if (idx !== -1) order.splice(idx, 1);
    order.push(mid);
    return order;
  }

  function rebuild() {
    // Remove old strands
    for (const s of strands) {
      scene.remove(s.group);
    }
    strands = [];

    const configs = generateConfigs();
    const n = configs.length;
    const pools = splitPools(allImages, n);
    const drawOrder = generateDrawOrder(n);

    // Compute Y positions
    const totalHeight =
      configs.reduce((sum, s) => sum + s.height, 0) +
      params.gap * (n - 1);
    let y = totalHeight / 2;

    const yPositions: number[] = [];
    for (const cfg of configs) {
      yPositions.push(y - cfg.height / 2);
      y -= cfg.height + params.gap;
    }

    // Create strands in draw order
    const newStrands: Strand[] = new Array(n);
    for (const i of drawOrder) {
      const zPos = drawOrder.indexOf(i);
      const strand = new Strand(pools[i]!, configs[i]!, yPositions[i]!, zPos);
      scene.add(strand.group);
      newStrands[i] = strand;
    }
    strands = newStrands;
  }

  rebuild();

  // Tweakpane
  const pane = new Pane({ title: "Aligned Waters" });
  (pane as any).addBinding(params, "strandCount", { min: 3, max: 25, step: 1, label: "strands" });
  (pane as any).addBinding(params, "scaleFactor", { min: 0.3, max: 3.0, step: 0.05, label: "scale" });
  (pane as any).addBinding(params, "gap", { min: -800, max: 800, step: 5, label: "gap" });
  (pane as any).addBinding(params, "stripWidthBase", { min: 30, max: 200, step: 5, label: "strip width" });
  (pane as any).addBinding(params, "speed", { min: 0.0, max: 5.0, step: 0.1, label: "speed" });
  (pane as any).on("change", (ev: any) => {
    if (ev.presetKey !== "speed") rebuild();
  });

  // Animation
  let lastTime = performance.now() / 1000;

  function animate() {
    requestAnimationFrame(animate);
    const now = performance.now() / 1000;
    const dt = Math.min(now - lastTime, 0.1);
    lastTime = now;

    for (const strand of strands) {
      if (strand) strand.update(dt * params.speed);
    }

    renderer.render(scene, camera);
  }

  animate();
}

init();
