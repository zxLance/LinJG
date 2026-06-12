import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const demoRoot = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(demoRoot, "..");
const port = Number(process.env.CESIUM_3DGS_PORT || 8765);

function contentType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".js") || filePath.endsWith(".mjs")) return "text/javascript; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".json")) return "application/json; charset=utf-8";
  if (filePath.endsWith(".glb")) return "model/gltf-binary";
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

  fs.readFile(filePath, (error, data) => {
    if (error) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    res.writeHead(200, {
      "Content-Type": contentType(filePath),
      "Cache-Control": "no-store"
    });
    res.end(data);
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Cesium 3DGS viewer: http://127.0.0.1:${port}/demo/viewer.html`);
});
