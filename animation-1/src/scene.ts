import * as THREE from "three";
import {
  CANVAS_WIDTH,
  CANVAS_HEIGHT,
  BG_COLOR_TOP,
  BG_COLOR_BOTTOM,
} from "./config";

export function createRenderer(): THREE.WebGLRenderer {
  const renderer = new THREE.WebGLRenderer({
    antialias: false,
    preserveDrawingBuffer: true,
  });
  renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  // Fit canvas in window while maintaining aspect ratio
  fitToWindow(renderer);
  window.addEventListener("resize", () => fitToWindow(renderer));

  document.body.appendChild(renderer.domElement);
  return renderer;
}

function fitToWindow(renderer: THREE.WebGLRenderer) {
  const aspect = CANVAS_WIDTH / CANVAS_HEIGHT;
  const windowAspect = window.innerWidth / window.innerHeight;

  let w: number, h: number;
  if (windowAspect > aspect) {
    // Window is wider — fit to height
    h = window.innerHeight;
    w = h * aspect;
  } else {
    // Window is taller — fit to width
    w = window.innerWidth;
    h = w / aspect;
  }

  renderer.setSize(w, h);
}

export function createCamera(): THREE.OrthographicCamera {
  const hw = CANVAS_WIDTH / 2;
  const hh = CANVAS_HEIGHT / 2;
  const camera = new THREE.OrthographicCamera(-hw, hw, hh, -hh, 0.1, 1000);
  camera.position.z = 100;
  return camera;
}

export function createBackground(scene: THREE.Scene) {
  // Fullscreen gradient quad
  const geo = new THREE.PlaneGeometry(CANVAS_WIDTH, CANVAS_HEIGHT);

  // Vertex colors for gradient
  const colors = new Float32Array(4 * 3); // 4 vertices, 3 channels
  const top = new THREE.Color(BG_COLOR_TOP);
  const bot = new THREE.Color(BG_COLOR_BOTTOM);

  // PlaneGeometry vertices: top-left, top-right, bottom-left, bottom-right
  // But Three.js PlaneGeometry order is: bottom-left, bottom-right, top-left, top-right
  // Actually it's more complex — let's use a shader instead

  const mat = new THREE.ShaderMaterial({
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec2 vUv;
      uniform vec3 colorTop;
      uniform vec3 colorBottom;
      void main() {
        vec3 color = mix(colorBottom, colorTop, vUv.y);
        gl_FragColor = vec4(color, 1.0);
      }
    `,
    uniforms: {
      colorTop: { value: new THREE.Color(BG_COLOR_TOP) },
      colorBottom: { value: new THREE.Color(BG_COLOR_BOTTOM) },
    },
    depthWrite: false,
  });

  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.z = -10; // behind everything
  scene.add(mesh);
}
