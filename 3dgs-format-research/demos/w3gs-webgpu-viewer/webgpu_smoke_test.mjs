#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { extname, join, normalize, resolve, sep } from "node:path";
import { spawn, spawnSync } from "node:child_process";

const viewerDir = resolve(import.meta.dirname);
const demosRoot = resolve(viewerDir, "..");
const args = parseArgs(process.argv.slice(2));
const chromePath = args.chrome || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const outputDir = resolve(args.output || join(demosRoot, "w3gs-from-ply", "huce-zhanting-10k-parent-summary-sh3", "evidence"));
const httpPort = Number(args.port || 8873);
const debugPort = Number(args.debugPort || 9333);
const sample = args.sample || "../w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3/";
const sampleDir = resolve(viewerDir, sample);

class CdpClient {
  static async connect(url) {
    const socket = new WebSocket(url);
    await new Promise((resolveOpen, reject) => {
      socket.addEventListener("open", resolveOpen, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    return new CdpClient(socket);
  }

  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve: resolveCall, reject, timer } = this.pending.get(message.id);
      this.pending.delete(message.id);
      clearTimeout(timer);
      if (message.error) reject(new Error(message.error.message));
      else resolveCall(message.result);
    });
    const rejectPending = () => {
      for (const { reject, timer } of this.pending.values()) {
        clearTimeout(timer);
        reject(new Error("Chrome DevTools connection closed before command completion."));
      }
      this.pending.clear();
    };
    socket.addEventListener("close", rejectPending);
    socket.addEventListener("error", rejectPending);
  }

  command(method, params = {}, timeoutMs = 10_000) {
    const id = this.nextId++;
    return new Promise((resolveCall, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Chrome DevTools command timed out: ${method}`));
      }, timeoutMs);
      this.pending.set(id, { resolve: resolveCall, reject, timer });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.socket.close();
  }
}

if (!existsSync(chromePath)) throw new Error(`Chrome not found: ${chromePath}`);
mkdirSync(outputDir, { recursive: true });

const server = createStaticServer(demosRoot, sampleDir);
await new Promise((resolveListen, reject) => {
  server.once("error", reject);
  server.listen(httpPort, "127.0.0.1", resolveListen);
});

const profileDir = join(tmpdir(), `w3gs-webgpu-smoke-${Date.now()}`);
const viewerUrl = `http://127.0.0.1:${httpPort}/w3gs-webgpu-viewer/?autoload=all&azimuth=0&sample=${encodeURIComponent(sample)}`;
const chrome = spawn(chromePath, [
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=${profileDir}`,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-extensions",
  "--no-proxy-server",
  "--window-size=1280,1200",
  viewerUrl,
], { stdio: "ignore", windowsHide: true });

let cdp;
try {
  const target = await waitForTarget(debugPort, "w3gs-webgpu-viewer", 20_000);
  cdp = await CdpClient.connect(target.webSocketDebuggerUrl);
  console.error("CDP connected");
  await cdp.command("Page.enable");
  await cdp.command("Runtime.enable");
  const state0 = await waitForViewerReady(cdp, 25_000);
  console.error("Viewer ready", JSON.stringify(state0));
  const shReference = await evaluate(cdp, "window.w3gsViewerDebug.verifyShReference()");
  console.error("CPU/WGSL SH reference", JSON.stringify(shReference));
  const canvasClip = await evaluate(cdp, `(() => {
    const r = document.getElementById("viewerCanvas").getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height};
  })()`);
  const image0 = await captureCanvas(cdp, canvasClip);
  console.error("Captured SH direction 0");
  const path0 = join(outputDir, "sh3-azimuth-0.png");
  writeFileSync(path0, image0);

  await evaluate(cdp, "window.w3gsViewerDebug.setShMode('dc')");
  console.error("Disabled high-order SH at fixed camera");
  await new Promise((resolveWait) => setTimeout(resolveWait, 400));
  const stateDc = await evaluate(cdp, "window.w3gsViewerDebug.getState()");
  const imageDc = await captureCanvas(cdp, canvasClip);
  const pathDc = join(outputDir, "sh3-dc-only-azimuth-0.png");
  writeFileSync(pathDc, imageDc);

  await evaluate(cdp, "window.w3gsViewerDebug.setShMode('full')");
  await evaluate(cdp, "window.w3gsViewerDebug.setAzimuth(180)");
  console.error("Changed camera azimuth to 180");
  await new Promise((resolveWait) => setTimeout(resolveWait, 800));
  const state180 = await evaluate(cdp, "window.w3gsViewerDebug.getState()");
  const image180 = await captureCanvas(cdp, canvasClip);
  console.error("Captured SH direction 180");
  const path180 = join(outputDir, "sh3-azimuth-180.png");
  writeFileSync(path180, image180);

  const report = {
    reportVersion: "1.0",
    generatedAtUtc: new Date().toISOString(),
    viewerUrl,
    chromePath,
    webgpuStatus: await evaluate(cdp, "document.getElementById('webgpuStatus').textContent"),
    shReference,
    stateAzimuth0: state0,
    stateDcOnlyAzimuth0: stateDc,
    stateAzimuth180: state180,
    screenshots: [fileEvidence(path0), fileEvidence(pathDc), fileEvidence(path180)],
    screenshotsDiffer: sha256(image0) !== sha256(image180),
    sameCameraFullVsDcDiffer: sha256(image0) !== sha256(imageDc),
    checks: {
      ready: state0.status === "Ready" && stateDc.status === "Ready" && state180.status === "Ready",
      sh3Profile: state0.profile === "raw-gaussian-sh3-v0" && state0.shDegree === 3,
      cpuWgslReference: shReference?.passed === true && shReference.maxAbsError <= 1e-5,
      payloadLoaded: state0.loadedChunks > 0 && state0.activeSplats > 0 && state0.gpuBytes > 0,
      fixedGeometryForShComparison:
        state0.azimuth === stateDc.azimuth &&
        state0.activeChunks === stateDc.activeChunks &&
        state0.activeSplats === stateDc.activeSplats &&
        state0.gpuBytes === stateDc.gpuBytes,
      shModeChanged: state0.shMode === "full" && stateDc.shMode === "dc",
      sameCameraShEffect: sha256(image0) !== sha256(imageDc),
      cameraChanged: state0.azimuth === 0 && state180.azimuth === 180,
      renderedImagesDiffer: sha256(image0) !== sha256(image180),
    },
  };
  report.passed = Object.values(report.checks).every(Boolean) && report.webgpuStatus === "WebGPU ready";
  writeFileSync(join(outputDir, "webgpu-smoke-report.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
  if (!report.passed) process.exitCode = 1;
} finally {
  if (cdp) cdp.close();
  if (process.platform === "win32" && chrome.pid) {
    spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
  } else {
    chrome.kill("SIGTERM");
  }
  await new Promise((resolveClose) => server.close(resolveClose));
}

function parseArgs(values) {
  const parsed = {};
  for (let index = 0; index < values.length; index += 2) {
    const key = values[index]?.replace(/^--/, "");
    if (key) parsed[key] = values[index + 1];
  }
  return parsed;
}

function createStaticServer(root, activeSampleDir) {
  const rootPrefix = `${resolve(root)}${sep}`;
  const payloadAliases = new Map();
  return createServer((request, response) => {
    const requestPath = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    if (requestPath.startsWith("/__w3gs_payload__/")) {
      const alias = requestPath.slice("/__w3gs_payload__/".length);
      const payloadPath = payloadAliases.get(alias);
      if (!payloadPath || !existsSync(payloadPath)) {
        response.writeHead(404).end("Payload alias not found");
        return;
      }
      sendFile(response, request.method, payloadPath);
      return;
    }
    let filePath = resolve(root, `.${normalize(requestPath)}`);
    if (!filePath.startsWith(rootPrefix)) {
      response.writeHead(403).end("Forbidden");
      return;
    }
    if (existsSync(filePath) && statSync(filePath).isDirectory()) filePath = join(filePath, "index.html");
    if (!existsSync(filePath) || !statSync(filePath).isFile()) {
      response.writeHead(404).end("Not found");
      return;
    }
    if (filePath === join(activeSampleDir, "scene.w3gs.json")) {
      const scene = JSON.parse(readFileSync(filePath, "utf8"));
      scene.files.payloadBaseUri = "/__w3gs_payload__/";
      sendJson(response, request.method, scene);
      return;
    }
    if (filePath === join(activeSampleDir, "chunks.w3gs.json")) {
      const chunks = JSON.parse(readFileSync(filePath, "utf8"));
      for (const [index, chunk] of chunks.chunks.entries()) {
        const alias = `payload-${index}`;
        payloadAliases.set(alias, resolve(activeSampleDir, "payload", chunk.uri));
        chunk.uri = alias;
      }
      sendJson(response, request.method, chunks);
      return;
    }
    sendFile(response, request.method, filePath);
  });
}

function sendJson(response, method, value) {
  const body = Buffer.from(`${JSON.stringify(value)}\n`, "utf8");
  response.writeHead(200, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": body.length,
    "Cache-Control": "no-store",
  });
  response.end(method === "HEAD" ? undefined : body);
}

function sendFile(response, method, filePath) {
  const body = readFileSync(filePath);
  response.writeHead(200, {
    "Content-Type": mimeType(filePath),
    "Content-Length": body.length,
    "Cache-Control": "no-store",
  });
  response.end(method === "HEAD" ? undefined : body);
}

function mimeType(path) {
  return ({
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".bin": "application/octet-stream",
  })[extname(path).toLowerCase()] || "application/octet-stream";
}

async function waitForTarget(port, urlFragment, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then((response) => response.json());
      const target = targets.find((item) => item.type === "page" && item.url.includes(urlFragment));
      if (target) return target;
    } catch {}
    await new Promise((resolveWait) => setTimeout(resolveWait, 200));
  }
  throw new Error("Timed out waiting for Chrome DevTools target.");
}

async function waitForViewerReady(cdp, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const state = await evaluate(cdp, "window.w3gsViewerDebug?.getState?.() || null");
    const webgpuStatus = await evaluate(cdp, "document.getElementById('webgpuStatus')?.textContent || ''");
    if (state?.status === "Ready" && state.activeSplats > 0) return state;
    if (state?.status === "Error") {
      const viewerLog = await evaluate(cdp, "document.getElementById('logOutput')?.textContent || ''");
      throw new Error(`Viewer error: ${webgpuStatus}\n${viewerLog}`);
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, 200));
  }
  throw new Error("Timed out waiting for WebGPU viewer payload/render readiness.");
}

async function evaluate(cdp, expression) {
  const result = await cdp.command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "Runtime.evaluate failed");
  return result.result.value;
}

async function captureCanvas(cdp, clip) {
  const result = await cdp.command("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: true,
    clip: { ...clip, scale: 1 },
  });
  return Buffer.from(result.data, "base64");
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function fileEvidence(path) {
  const bytes = readFileSync(path);
  return { path, bytes: bytes.length, sha256: sha256(bytes) };
}
