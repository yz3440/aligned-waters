/**
 * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially useful
 * for Docker builds.
 */
import "./src/env.js";

/** @type {import("next").NextConfig} */
const config = {
  // Emit a fully static site to ./out — the whole app renders client-side, so
  // there is nothing to run on a server. Deployed to Cloudflare as static assets.
  output: "export",
  // Required by `output: "export"`; every <Image> already passes `unoptimized`.
  images: { unoptimized: true },
};

export default config;
