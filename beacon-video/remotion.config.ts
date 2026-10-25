/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */
import { Config } from "@remotion/cli/config";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// Local-environment workaround: on this Mac, the Chromium 157 build Remotion
// downloads never fires requestAnimationFrame, so every render times out at
// "Waiting for root component to load". Chrome for Testing (already installed
// by Playwright) renders correctly. Override with BEACON_VIDEO_BROWSER; if
// neither exists, Remotion's default browser is used.
const findBrowser = (): string | null => {
  const fromEnv = process.env.BEACON_VIDEO_BROWSER;
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;
  const root = path.join(os.homedir(), "Library/Caches/ms-playwright");
  if (!fs.existsSync(root)) return null;
  const candidates = fs
    .readdirSync(root)
    .filter((d) => d.startsWith("chromium_headless_shell"))
    .sort()
    .reverse()
    .map((d) => path.join(root, d, "chrome-headless-shell-mac-arm64/chrome-headless-shell"));
  return candidates.find((p) => fs.existsSync(p)) ?? null;
};
const browser = findBrowser();
if (browser) Config.setBrowserExecutable(browser);

Config.setRspack(true);
// PNG frames + bt709 give standard limited-range yuv420p with color tags.
// (JPEG frames produced full-range yuvj420p tagged bt470bg.)
Config.setVideoImageFormat("png");
Config.setColorSpace("bt709");
Config.setOverwriteOutput(true);
Config.setDefaultPremountInSeconds(2);

// Beacon's own services use 3000 (Next.js), 8000 (API) and 8501 (Streamlit).
// Keep Remotion's Studio and its render server well clear of them.
Config.setStudioPort(3123);
Config.setRendererPort(3124);

// CapCut-friendly delivery: H.264 in MP4, yuv420p, high quality.
Config.setCodec("h264");
Config.setPixelFormat("yuv420p");
Config.setCrf(16);
