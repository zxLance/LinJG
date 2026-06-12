import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const demoRoot = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(demoRoot, "..");
const port = Number(process.env.CESIUM_3DGS_DEBUG_PORT || 8766);
const debugPort = 9333;
const chromePath = process.env.CHROME_PATH || "chrome.exe";
const userDataDir = path.join(demoRoot, ".chrome-debug-profile");
const screenshotPath = path.join(demoRoot, "debug-screenshot.png");

function contentType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".json")) return "application/json; charset=utf-8";
  if (filePath.endsWith(".png")) return "image/png";
  return "application/octet-stream";
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${port}`);
  const rel =
    url.pathname === "/" || url.pathname === "/viewer.html"
      ? "demo/viewer.html"
      : decodeURIComponent(url.pathname.slice(1));
  const filePath = path.normalize(path.join(root, rel));
  if (!filePath.startsWith(root)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    res.writeHead(200, { "Content-Type": contentType(filePath), "Cache-Control": "no-store" });
    res.end(data);
  });
});

await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
fs.mkdirSync(userDataDir, { recursive: true });

const chromeArgs = [
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=${userDataDir}`,
  "--no-first-run",
  "--no-default-browser-check",
  "--autoplay-policy=no-user-gesture-required",
  "--window-size=1280,850",
  "--disable-background-timer-throttling",
  "--disable-renderer-backgrounding",
  `http://127.0.0.1:${port}/demo/viewer.html`
];

const chrome = spawn(chromePath, chromeArgs, {
  detached: true,
  stdio: "ignore"
});
chrome.unref();

async function getJson(url, tries = 60) {
  let lastError;
  for (let i = 0; i < tries; i++) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw lastError;
}

const tabs = await getJson(`http://127.0.0.1:${debugPort}/json`);
const tab = tabs.find((item) => item.url.includes("demo/viewer.html")) || tabs[0];
const ws = new WebSocket(tab.webSocketDebuggerUrl);
const pending = new Map();
let nextId = 1;
const logs = [];

ws.addEventListener("message", (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
    return;
  }
  if (msg.method === "Runtime.consoleAPICalled") {
    logs.push({ type: msg.params.type, args: msg.params.args.map((arg) => arg.value ?? arg.description) });
  }
  if (msg.method === "Runtime.exceptionThrown") {
    logs.push({ type: "exception", args: [msg.params.exceptionDetails?.text, msg.params.exceptionDetails?.exception?.description] });
  }
  if (msg.method === "Log.entryAdded") {
    logs.push({ type: msg.params.entry.level, args: [msg.params.entry.text] });
  }
});

await new Promise((resolve, reject) => {
  ws.addEventListener("open", resolve, { once: true });
  ws.addEventListener("error", reject, { once: true });
});

function send(method, params = {}) {
  const id = nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

await send("Runtime.enable");
await send("Log.enable");
await send("Page.enable");

for (let i = 0; i < 45; i++) {
  await new Promise((resolve) => setTimeout(resolve, 1000));
  const result = await send("Runtime.evaluate", {
    expression: `({
      text: document.getElementById("status")?.textContent || "",
      renderError: window.__renderError || "",
      canvas: (() => {
        const c = document.querySelector("canvas");
        return c ? { width: c.width, height: c.height } : null;
      })()
    })`,
    returnByValue: true
  });
  const value = result.result.value;
  if (value?.text?.includes("visible points/frame:") && !value.text.includes("visible points/frame: 0")) {
    break;
  }
  if (value?.text?.includes("rendering stopped")) {
    break;
  }
}

const finalEval = await send("Runtime.evaluate", {
  expression: `({
    status: document.getElementById("status")?.textContent || "",
    renderError: window.__renderError || "",
    title: document.title,
    href: location.href
  })`,
  returnByValue: true
});

const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));

const output = {
  page: finalEval.result.value,
  logs: logs.slice(-30),
  screenshotPath
};

console.log(JSON.stringify(output, null, 2));

await send("Browser.close").catch(() => {});
ws.close();
server.close();
