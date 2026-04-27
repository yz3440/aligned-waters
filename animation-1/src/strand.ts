import * as THREE from "three";
import type { ImageRecord } from "./data";
import type { StrandConfig } from "./config";
import { CANVAS_WIDTH, DURATION_SECONDS } from "./config";

interface StripPlane {
  mesh: THREE.Mesh;
  poolIdx: number;
}

export class Strand {
  group: THREE.Group;
  private pool: ImageRecord[];
  private config: StrandConfig;
  private strips: StripPlane[] = [];
  private nextPoolIdx = 0;
  private textureLoader = new THREE.TextureLoader();
  private stripWidth: number; // fixed width per strand
  private scrollSpeed: number;

  constructor(
    pool: ImageRecord[],
    config: StrandConfig,
    yPosition: number,
    zPosition: number
  ) {
    this.pool = pool;
    this.config = config;
    this.group = new THREE.Group();
    this.group.position.y = yPosition;
    this.group.position.z = zPosition;
    this.stripWidth = config.stripWidth;

    // Scroll speed: traverse entire pool in DURATION / scrollCycles
    const totalPoolWidth = pool.length * this.stripWidth;
    this.scrollSpeed =
      (totalPoolWidth * config.scrollCycles) / DURATION_SECONDS;

    this.fillViewport();
  }

  private getStripHeight(rec: ImageRecord): number {
    // Fixed width, height varies by aspect ratio (like the frontend)
    return this.stripWidth * (rec.height / rec.width);
  }

  private fillViewport() {
    let x = -CANVAS_WIDTH;
    while (x < CANVAS_WIDTH) {
      this.createStrip(x);
      x += this.stripWidth;
    }
  }

  private createStrip(xLeft: number): StripPlane {
    const idx = this.nextPoolIdx;
    const rec = this.pool[idx % this.pool.length];
    this.nextPoolIdx = (this.nextPoolIdx + 1) % this.pool.length;

    const w = this.stripWidth;
    const h = this.getStripHeight(rec);

    const geo = new THREE.PlaneGeometry(w, h);
    const mat = new THREE.MeshBasicMaterial({ color: 0x888888 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.x = xLeft + w / 2;

    // Horizon alignment: shift plane vertically so horizon sits at y=0 (strand center)
    // The horizon is at horizon_y fraction from the top of the image.
    // In the plane, center is y=0, top is +h/2, bottom is -h/2.
    // Horizon pixel from top = horizon_y * h, from center = h/2 - horizon_y * h
    // We want horizon at y=0, so shift by -(h/2 - horizon_y * h) = horizon_y*h - h/2
    mesh.position.y = (rec.horizon_y - 0.5) * h;

    this.group.add(mesh);

    const strip: StripPlane = { mesh, poolIdx: idx };
    this.strips.push(strip);

    this.loadTexture(strip, rec);
    return strip;
  }

  private loadTexture(strip: StripPlane, rec: ImageRecord) {
    const mat = strip.mesh.material as THREE.MeshBasicMaterial;

    this.textureLoader.load(`/images_resized/${rec.filename}`, (tex) => {
      if (mat.map) mat.map.dispose();

      tex.colorSpace = THREE.SRGBColorSpace;
      // Full image, no cropping — the plane is already sized to match
      tex.wrapS = THREE.ClampToEdgeWrapping;
      tex.wrapT = THREE.ClampToEdgeWrapping;

      mat.map = tex;
      mat.color.set(0xffffff);
      mat.needsUpdate = true;
    });
  }

  update(dt: number) {
    const scrollDelta = this.scrollSpeed * dt;

    for (const strip of this.strips) {
      strip.mesh.position.x -= scrollDelta;
    }

    const leftLimit = -CANVAS_WIDTH;

    for (const strip of this.strips) {
      const rightEdge = strip.mesh.position.x + this.stripWidth / 2;
      if (rightEdge < leftLimit) {
        // Find rightmost edge
        let maxRight = -Infinity;
        for (const s of this.strips) {
          const r = s.mesh.position.x + this.stripWidth / 2;
          if (r > maxRight) maxRight = r;
        }

        // Get next image
        const rec = this.pool[this.nextPoolIdx % this.pool.length];
        this.nextPoolIdx = (this.nextPoolIdx + 1) % this.pool.length;

        const newH = this.getStripHeight(rec);

        // Update geometry and position
        strip.mesh.geometry.dispose();
        strip.mesh.geometry = new THREE.PlaneGeometry(this.stripWidth, newH);
        strip.mesh.position.x = maxRight + this.stripWidth / 2;
        strip.mesh.position.y = (rec.horizon_y - 0.5) * newH;

        this.loadTexture(strip, rec);
      }
    }
  }
}
