export const CANVAS_WIDTH = 1200;
export const CANVAS_HEIGHT = 1724;
export const DURATION_SECONDS = 480; // 8 minutes
export const NUM_STRANDS = 15;

export interface StrandConfig {
  stripWidth: number;
  height: number;
  scrollCycles: number;
}

// 15 strands: center tallest, tapers outward symmetrically
export const STRAND_CONFIGS: StrandConfig[] = [
  { stripWidth: 50,  height: 80,  scrollCycles: 1 },  // 0: edge
  { stripWidth: 55,  height: 90,  scrollCycles: 2 },  // 1
  { stripWidth: 60,  height: 100, scrollCycles: 1 },  // 2
  { stripWidth: 65,  height: 115, scrollCycles: 3 },  // 3
  { stripWidth: 70,  height: 130, scrollCycles: 2 },  // 4
  { stripWidth: 80,  height: 150, scrollCycles: 1 },  // 5
  { stripWidth: 90,  height: 175, scrollCycles: 2 },  // 6
  { stripWidth: 100, height: 200, scrollCycles: 1 },  // 7: center (tallest)
  { stripWidth: 90,  height: 175, scrollCycles: 2 },  // 8
  { stripWidth: 80,  height: 150, scrollCycles: 3 },  // 9
  { stripWidth: 70,  height: 130, scrollCycles: 1 },  // 10
  { stripWidth: 65,  height: 115, scrollCycles: 2 },  // 11
  { stripWidth: 60,  height: 100, scrollCycles: 1 },  // 12
  { stripWidth: 55,  height: 90,  scrollCycles: 3 },  // 13
  { stripWidth: 50,  height: 80,  scrollCycles: 2 },  // 14: edge
];

export const STRAND_GAP = -20; // negative = overlap

// Draw order: edges first, center last (on top)
export const DRAW_ORDER = [0, 14, 1, 13, 2, 12, 3, 11, 4, 10, 5, 9, 6, 8, 7];

// Background gradient (matches frontend)
export const BG_COLOR_TOP = 0xabdbff;
export const BG_COLOR_BOTTOM = 0x57748a;
