import { NUM_STRANDS } from "./config";

export interface ImageRecord {
  filename: string;
  width: number;
  height: number;
  horizon_y: number;
  created_at: string;
}

export async function loadManifest(): Promise<ImageRecord[]> {
  const res = await fetch("/manifest.json");
  const images: ImageRecord[] = await res.json();
  // Already sorted by created_at from the Python script
  return images;
}

export function splitPools(
  images: ImageRecord[],
  numStrands: number = NUM_STRANDS
): ImageRecord[][] {
  const pools: ImageRecord[][] = Array.from({ length: numStrands }, () => []);
  for (let i = 0; i < images.length; i++) {
    pools[i % numStrands].push(images[i]);
  }
  return pools;
}
