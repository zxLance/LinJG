const DEFAULT_SAMPLE_BASE = "../w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3/";
const PROFILE_DEFINITIONS = {
  "raw-gaussian-v0": {
    schemaId: "gaussian-basic-v0",
    floatsPerSplat: 14,
    bytesPerSplat: 56,
    shDegree: 0
  },
  "raw-gaussian-sh3-v0": {
    schemaId: "gaussian-sh3-v0",
    floatsPerSplat: 59,
    bytesPerSplat: 236,
    shDegree: 3
  }
};

const queryParams = new URLSearchParams(window.location.search);
const querySample = queryParams.get("sample");
const SAMPLE_BASE = ensureTrailingSlash(querySample || DEFAULT_SAMPLE_BASE);

const els = {
  canvas: document.getElementById("viewerCanvas"),
  statusPill: document.getElementById("statusPill"),
  webgpuStatus: document.getElementById("webgpuStatus"),
  sampleName: document.getElementById("sampleName"),
  lodMode: document.getElementById("lodMode"),
  codecProfile: document.getElementById("codecProfile"),
  shDegree: document.getElementById("shDegree"),
  nodeCount: document.getElementById("nodeCount"),
  chunkCount: document.getElementById("chunkCount"),
  activeChunkCount: document.getElementById("activeChunkCount"),
  splatCount: document.getElementById("splatCount"),
  gpuBytes: document.getElementById("gpuBytes"),
  frameTime: document.getElementById("frameTime"),
  log: document.getElementById("logOutput"),
  loadStartup: document.getElementById("loadStartupButton"),
  loadLeaves: document.getElementById("loadLeavesButton"),
  loadAll: document.getElementById("loadAllButton"),
  clear: document.getElementById("clearButton"),
  pointScale: document.getElementById("pointScale"),
  opacityBoost: document.getElementById("opacityBoost"),
  cameraAzimuth: document.getElementById("cameraAzimuth"),
  cameraAzimuthValue: document.getElementById("cameraAzimuthValue"),
  autoOrbit: document.getElementById("autoOrbit"),
  fullSh3: document.getElementById("fullSh3")
};

const app = {
  sampleRoot: new URL(SAMPLE_BASE, window.location.href),
  scene: null,
  nodesDoc: null,
  chunksDoc: null,
  profile: null,
  nodeById: new Map(),
  layerById: new Map(),
  chunkById: new Map(),
  payloadCache: new Map(),
  loadedChunkData: new Map(),
  loadedChunkIds: new Set(),
  activeChunkIds: new Set(),
  activeFloats: new Float32Array(0),
  renderer: null,
  shMode: queryParams.get("shMode") === "dc" ? "dc" : "full",
  lastFrameAt: performance.now()
};

els.loadStartup.addEventListener("click", () => loadChunkSet(startupChunkIds(), "startup"));
els.loadLeaves.addEventListener("click", () => loadChunkSet(leafChunkIds(), "leaf chunks"));
els.loadAll.addEventListener("click", () => loadChunkSet([...app.chunkById.keys()], "all chunks"));
els.clear.addEventListener("click", clearLoadedChunks);
els.pointScale.addEventListener("input", () => app.renderer?.render());
els.opacityBoost.addEventListener("input", () => app.renderer?.render());
els.cameraAzimuth.addEventListener("input", updateCameraUi);
els.fullSh3.addEventListener("change", () => setShMode(els.fullSh3.checked ? "full" : "dc"));

initialize();

async function initialize() {
  setControlsEnabled(false);
  setStatus("Loading manifests");
  try {
    await loadW3gsManifest();
    renderManifestStats();
    app.renderer = await createWebGpuRenderer(els.canvas, app.profile);
    els.fullSh3.checked = app.shMode === "full";
    els.fullSh3.disabled = app.profile.shDegree === 0;
    setStatus("Ready");
    els.webgpuStatus.textContent = "WebGPU ready";
    setControlsEnabled(true);
    const requestedAzimuth = Number(queryParams.get("azimuth"));
    if (Number.isFinite(requestedAzimuth)) els.cameraAzimuth.value = String(requestedAzimuth);
    updateCameraUi();
    const autoLoad = queryParams.get("autoload");
    if (autoLoad === "startup") await loadChunkSet(startupChunkIds(), "startup");
    if (autoLoad === "leaves") await loadChunkSet(leafChunkIds(), "leaf chunks");
    if (autoLoad === "all") await loadChunkSet([...app.chunkById.keys()], "all chunks");
    requestAnimationFrame(frameLoop);
    log(`Loaded ${app.profile.id} manifests in replacement mode from ${SAMPLE_BASE}`);
  } catch (error) {
    console.error(error);
    setStatus("Error", true);
    els.webgpuStatus.textContent = error.message;
    log(`ERROR: ${error.message}`);
  }
}

async function loadW3gsManifest() {
  const scene = await fetchJson(new URL("scene.w3gs.json", app.sampleRoot).href);
  const nodesDoc = await fetchJson(new URL(scene.files.nodes, app.sampleRoot).href);
  const chunksDoc = await fetchJson(new URL(scene.files.chunks, app.sampleRoot).href);

  app.scene = scene;
  app.nodesDoc = nodesDoc;
  app.chunksDoc = chunksDoc;
  app.nodeById = new Map(nodesDoc.nodes.map((node) => [node.id, node]));
  app.chunkById = new Map(chunksDoc.chunks.map((chunk) => [chunk.id, chunk]));
  app.layerById = new Map();
  for (const node of nodesDoc.nodes) {
    for (const layer of node.layers) app.layerById.set(layer.id, { ...layer, node: node.id });
  }

  const missing = [...app.layerById.values()]
    .filter((layer) => !app.chunkById.has(layer.chunk))
    .map((layer) => layer.chunk);
  if (missing.length) throw new Error(`Layer references missing chunks: ${missing.join(", ")}`);
  app.profile = resolveManifestProfile(scene, chunksDoc);
}

function resolveManifestProfile(scene, chunksDoc) {
  const codecById = new Map((scene.codecs || []).map((codec) => [codec.id, codec]));
  const codecIds = new Set(chunksDoc.chunks.map((chunk) => chunk.codec));
  if (codecIds.size !== 1) throw new Error("Viewer currently requires one homogeneous raw codec per sample.");
  const id = [...codecIds][0];
  const definition = PROFILE_DEFINITIONS[id];
  if (!definition) throw new Error(`Unsupported payload codec: ${id}`);
  const codec = codecById.get(id);
  if (!codec) throw new Error(`Codec ${id} is not declared in scene.codecs.`);
  const schema = chunksDoc.attributeSchemas?.[codec.attributeSchema];
  if (!schema) throw new Error(`Missing attribute schema: ${codec.attributeSchema}`);
  if (codec.attributeSchema !== definition.schemaId || schema.bytesPerSplat !== definition.bytesPerSplat) {
    throw new Error(`${id} schema/stride does not match the known W3GS profile.`);
  }
  return { id, schema, ...definition };
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  return response.json();
}

function startupChunkIds() {
  return (app.scene.entry?.startupSet || [])
    .map((layerId) => app.layerById.get(layerId)?.chunk)
    .filter(Boolean);
}

function leafChunkIds() {
  const ids = [];
  for (const node of app.nodesDoc.nodes) {
    if ((node.children || []).length) continue;
    for (const layer of node.layers) ids.push(layer.chunk);
  }
  return ids;
}

async function loadChunkSet(chunkIds, label) {
  if (!app.renderer) return;
  const ids = [...new Set(chunkIds)].filter((id) => !app.loadedChunkIds.has(id));
  if (!ids.length) {
    log(`No new ${label} to load.`);
    rebuildActivePayload();
    return;
  }
  setStatus(`Loading ${label}`);
  try {
    for (const id of ids) {
      const chunk = app.chunkById.get(id);
      if (!chunk) continue;
      app.loadedChunkData.set(id, await readChunkFloats(chunk));
      app.loadedChunkIds.add(id);
      log(`Loaded ${id}: ${chunk.splatCount} splats, ${formatBytes(chunk.byteLength)}`);
    }
    rebuildActivePayload();
    setStatus("Ready");
  } catch (error) {
    console.error(error);
    setStatus("Error", true);
    log(`ERROR while loading ${label}: ${error.message}`);
  }
}

async function readChunkFloats(chunk) {
  if (chunk.codec !== app.profile.id || chunk.attributeSchema !== app.profile.schemaId) {
    throw new Error(`${chunk.id} does not match active profile ${app.profile.id}`);
  }
  const payload = await fetchPayload(chunk.uri);
  if (chunk.byteOffset + chunk.byteLength > payload.byteLength) {
    throw new Error(`${chunk.id} range ${chunk.byteOffset}+${chunk.byteLength} exceeds ${chunk.uri} (${payload.byteLength} bytes)`);
  }
  if (chunk.byteOffset % 4 !== 0 || chunk.byteLength % 4 !== 0) throw new Error(`${chunk.id} range is not float-aligned`);
  const floats = new Float32Array(payload, chunk.byteOffset, chunk.byteLength / 4);
  if (floats.length !== chunk.splatCount * app.profile.floatsPerSplat) {
    throw new Error(`${chunk.id} does not match ${app.profile.id} stride`);
  }
  return floats;
}

async function fetchPayload(uri) {
  if (app.payloadCache.has(uri)) return app.payloadCache.get(uri);
  const payloadRoot = app.scene.files.payloadBaseUri || "payload/";
  const url = new URL(`${payloadRoot}${uri}`, app.sampleRoot).href;
  log(`Fetching payload ${url}`);
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  log(`Payload response ${response.status}, content-length=${response.headers.get("content-length") || "unknown"}`);
  const buffer = await response.arrayBuffer();
  log(`Payload decoded: ${buffer.byteLength} bytes`);
  app.payloadCache.set(uri, buffer);
  return buffer;
}

function rebuildActivePayload() {
  const activeIds = activeChunkIdsByReplacement();
  const arrays = activeIds.map((id) => app.loadedChunkData.get(id)).filter(Boolean);
  app.activeChunkIds = new Set(activeIds);
  app.activeFloats = mergeFloatArrays(arrays);
  app.renderer?.upload(app.activeFloats);
  app.renderer?.render();
  renderRuntimeStats();
  log(`Active replacement set: ${activeIds.length} chunks, ${formatInteger(app.renderer?.splatCount || 0)} splats.`);
}

function activeChunkIdsByReplacement() {
  const rootId = app.scene.entry?.rootNode || app.nodesDoc.tree?.root || "root";
  return activeChunksForNode(rootId);
}

function activeChunksForNode(nodeId) {
  const node = app.nodeById.get(nodeId);
  if (!node) return [];
  const childChunks = [];
  for (const childId of node.children || []) childChunks.push(...activeChunksForNode(childId));
  if (childChunks.length) return childChunks;
  return [...node.layers]
    .sort((a, b) => a.level - b.level)
    .map((layer) => layer.chunk)
    .filter((chunkId) => app.loadedChunkIds.has(chunkId));
}

function mergeFloatArrays(arrays) {
  const totalLength = arrays.reduce((sum, array) => sum + array.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const array of arrays) {
    merged.set(array, offset);
    offset += array.length;
  }
  return merged;
}

function clearLoadedChunks() {
  app.loadedChunkData.clear();
  app.loadedChunkIds.clear();
  app.activeChunkIds.clear();
  app.activeFloats = new Float32Array(0);
  app.renderer?.upload(app.activeFloats);
  app.renderer?.render();
  renderRuntimeStats();
  log("Cleared loaded and active chunks.");
}

async function createWebGpuRenderer(canvas, profile) {
  if (!("gpu" in navigator)) throw new Error("WebGPU is not available. Use a current Chrome or Edge build.");
  const adapter = await navigator.gpu.requestAdapter();
  if (!adapter) throw new Error("No WebGPU adapter found.");
  const device = await adapter.requestDevice();
  const context = canvas.getContext("webgpu");
  const format = navigator.gpu.getPreferredCanvasFormat();
  const shader = device.createShaderModule({ code: shaderSource() });
  const compilation = await shader.getCompilationInfo();
  const shaderErrors = compilation.messages.filter((message) => message.type === "error");
  if (shaderErrors.length) throw new Error(`WGSL compilation failed: ${shaderErrors[0].message}`);

  const pipeline = device.createRenderPipeline({
    label: `${profile.id} disc pipeline`,
    layout: "auto",
    vertex: { module: shader, entryPoint: "vsMain" },
    fragment: {
      module: shader,
      entryPoint: "fsMain",
      targets: [{
        format,
        blend: {
          color: { srcFactor: "src-alpha", dstFactor: "one-minus-src-alpha", operation: "add" },
          alpha: { srcFactor: "one", dstFactor: "one-minus-src-alpha", operation: "add" }
        }
      }]
    },
    primitive: { topology: "triangle-list" }
  });

  const uniformBuffer = device.createBuffer({
    label: "viewer uniforms",
    size: 128,
    usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST
  });
  let splatBuffer = null;
  let bindGroup = null;
  let splatCount = 0;
  let splatBufferBytes = 0;
  let configuredWidth = 0;
  let configuredHeight = 0;

  function configureCanvas() {
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.floor(canvas.clientWidth * dpr));
    const height = Math.max(1, Math.floor(canvas.clientHeight * dpr));
    if (width === configuredWidth && height === configuredHeight) return;
    configuredWidth = width;
    configuredHeight = height;
    canvas.width = width;
    canvas.height = height;
    context.configure({ device, format, alphaMode: "premultiplied" });
  }

  function upload(floatData) {
    splatCount = Math.floor(floatData.length / profile.floatsPerSplat);
    if (splatBuffer) splatBuffer.destroy();
    splatBufferBytes = floatData.byteLength;
    splatBuffer = device.createBuffer({
      label: `${profile.id} splats`,
      size: Math.max(4, floatData.byteLength),
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST
    });
    if (floatData.byteLength) device.queue.writeBuffer(splatBuffer, 0, floatData.buffer, floatData.byteOffset, floatData.byteLength);
    bindGroup = device.createBindGroup({
      layout: pipeline.getBindGroupLayout(0),
      entries: [
        { binding: 0, resource: { buffer: splatBuffer } },
        { binding: 1, resource: { buffer: uniformBuffer } }
      ]
    });
  }

  function writeUniforms() {
    const camera = cameraFrame(app.scene.bounds, Number(els.cameraAzimuth.value));
    const uniforms = new Float32Array(32);
    uniforms.set([...camera.center, camera.sceneRadius], 0);
    uniforms.set([...camera.position, 0], 4);
    uniforms.set([...camera.right, 0], 8);
    uniforms.set([...camera.up, 0], 12);
    uniforms.set([...camera.forward, 0], 16);
    uniforms.set([canvas.width, canvas.height, Number(els.pointScale.value), 1.2], 20);
    uniforms.set([24, Number(els.opacityBoost.value), profile.floatsPerSplat, profile.shDegree], 24);
    uniforms.set([app.shMode === "full" ? 1 : 0, 0, 0, 0], 28);
    device.queue.writeBuffer(uniformBuffer, 0, uniforms);
  }

  function render() {
    configureCanvas();
    writeUniforms();
    const encoder = device.createCommandEncoder();
    const pass = encoder.beginRenderPass({
      colorAttachments: [{
        view: context.getCurrentTexture().createView(),
        clearValue: { r: 0.03, g: 0.05, b: 0.09, a: 1 },
        loadOp: "clear",
        storeOp: "store"
      }]
    });
    if (bindGroup && splatCount > 0) {
      pass.setPipeline(pipeline);
      pass.setBindGroup(0, bindGroup);
      pass.draw(splatCount * 6);
    }
    pass.end();
    device.queue.submit([encoder.finish()]);
  }

  async function verifyShReference() {
    const values = new Float32Array(62);
    values.set([0.2, -0.1, 0.35], 11);
    for (let channel = 0; channel < 3; channel += 1) {
      for (let coefficient = 1; coefficient < 16; coefficient += 1) {
        values[14 + channel * 15 + coefficient - 1] = ((channel + 1) * 17 + coefficient * 3 - 31) * 0.0025;
      }
    }
    const direction = normalize3([0.3, -0.4, 0.8660254037844386]);
    values.set(direction, 59);
    const expected = evaluateShReferenceCpu(values, direction);
    const module = device.createShaderModule({ code: shReferenceComputeSource() });
    const pipeline = device.createComputePipeline({ layout: "auto", compute: { module, entryPoint: "main" } });
    const input = device.createBuffer({ size: values.byteLength, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
    const output = device.createBuffer({ size: 16, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC });
    const readback = device.createBuffer({ size: 16, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
    device.queue.writeBuffer(input, 0, values);
    const group = device.createBindGroup({
      layout: pipeline.getBindGroupLayout(0),
      entries: [
        { binding: 0, resource: { buffer: input } },
        { binding: 1, resource: { buffer: output } }
      ]
    });
    const encoder = device.createCommandEncoder();
    const pass = encoder.beginComputePass();
    pass.setPipeline(pipeline);
    pass.setBindGroup(0, group);
    pass.dispatchWorkgroups(1);
    pass.end();
    encoder.copyBufferToBuffer(output, 0, readback, 0, 16);
    device.queue.submit([encoder.finish()]);
    await readback.mapAsync(GPUMapMode.READ);
    const actual = Array.from(new Float32Array(readback.getMappedRange().slice(0, 12)));
    readback.unmap();
    input.destroy();
    output.destroy();
    readback.destroy();
    const maxAbsError = Math.max(...actual.map((value, index) => Math.abs(value - expected[index])));
    return { expected, actual, maxAbsError, passed: maxAbsError <= 1e-5 };
  }

  upload(new Float32Array(0));
  window.addEventListener("resize", render);
  return {
    upload,
    render,
    verifyShReference,
    get splatCount() { return splatCount; },
    get gpuBufferBytes() { return splatBufferBytes; }
  };
}

function shReferenceComputeSource() {
  return /* wgsl */ `
@group(0) @binding(0) var<storage, read> values: array<f32>;
@group(0) @binding(1) var<storage, read_write> outputColor: array<f32>;

fn shBasis(index: u32, d: vec3<f32>) -> f32 {
  let x = d.x; let y = d.y; let z = d.z;
  let xx = x * x; let yy = y * y; let zz = z * z;
  switch index {
    case 0u: { return 0.28209479177387814; }
    case 1u: { return -0.4886025119029199 * y; }
    case 2u: { return 0.4886025119029199 * z; }
    case 3u: { return -0.4886025119029199 * x; }
    case 4u: { return 1.0925484305920792 * x * y; }
    case 5u: { return -1.0925484305920792 * y * z; }
    case 6u: { return 0.31539156525252005 * (2.0 * zz - xx - yy); }
    case 7u: { return -1.0925484305920792 * x * z; }
    case 8u: { return 0.5462742152960396 * (xx - yy); }
    case 9u: { return -0.5900435899266435 * y * (3.0 * xx - yy); }
    case 10u: { return 2.890611442640554 * x * y * z; }
    case 11u: { return -0.4570457994644658 * y * (4.0 * zz - xx - yy); }
    case 12u: { return 0.3731763325901154 * z * (2.0 * zz - 3.0 * xx - 3.0 * yy); }
    case 13u: { return -0.4570457994644658 * x * (4.0 * zz - xx - yy); }
    case 14u: { return 1.445305721320277 * z * (xx - yy); }
    case 15u: { return -0.5900435899266435 * x * (xx - 3.0 * yy); }
    default: { return 0.0; }
  }
}

fn coefficient(channel: u32, index: u32) -> f32 {
  if (index == 0u) { return values[11u + channel]; }
  return values[14u + channel * 15u + index - 1u];
}

@compute @workgroup_size(1)
fn main() {
  let direction = normalize(vec3<f32>(values[59], values[60], values[61]));
  var color = vec3<f32>(0.5);
  for (var index = 0u; index < 16u; index = index + 1u) {
    color = color + shBasis(index, direction) * vec3<f32>(
      coefficient(0u, index), coefficient(1u, index), coefficient(2u, index)
    );
  }
  color = max(color, vec3<f32>(0.0));
  outputColor[0] = color.x; outputColor[1] = color.y; outputColor[2] = color.z; outputColor[3] = 1.0;
}`;
}

function evaluateShReferenceCpu(values, direction) {
  const basis = shBasisCpu(direction);
  const color = [0.5, 0.5, 0.5];
  for (let channel = 0; channel < 3; channel += 1) {
    color[channel] += basis[0] * values[11 + channel];
    for (let coefficient = 1; coefficient < 16; coefficient += 1) {
      color[channel] += basis[coefficient] * values[14 + channel * 15 + coefficient - 1];
    }
    color[channel] = Math.max(0, color[channel]);
  }
  return color;
}

function shBasisCpu([x, y, z]) {
  const xx = x * x; const yy = y * y; const zz = z * z;
  return [
    0.28209479177387814,
    -0.4886025119029199 * y,
    0.4886025119029199 * z,
    -0.4886025119029199 * x,
    1.0925484305920792 * x * y,
    -1.0925484305920792 * y * z,
    0.31539156525252005 * (2 * zz - xx - yy),
    -1.0925484305920792 * x * z,
    0.5462742152960396 * (xx - yy),
    -0.5900435899266435 * y * (3 * xx - yy),
    2.890611442640554 * x * y * z,
    -0.4570457994644658 * y * (4 * zz - xx - yy),
    0.3731763325901154 * z * (2 * zz - 3 * xx - 3 * yy),
    -0.4570457994644658 * x * (4 * zz - xx - yy),
    1.445305721320277 * z * (xx - yy),
    -0.5900435899266435 * x * (xx - 3 * yy)
  ];
}

function cameraFrame(bounds, azimuthDegrees) {
  const min = bounds.min;
  const max = bounds.max;
  const center = min.map((value, index) => (value + max[index]) * 0.5);
  const diagonal = Math.hypot(max[0] - min[0], max[1] - min[1], max[2] - min[2]);
  const sceneRadius = Math.max(0.001, diagonal * 0.5);
  const azimuth = azimuthDegrees * Math.PI / 180;
  const elevation = 22 * Math.PI / 180;
  const distance = sceneRadius * 2.6;
  const position = [
    center[0] + Math.sin(azimuth) * Math.cos(elevation) * distance,
    center[1] + Math.sin(elevation) * distance,
    center[2] + Math.cos(azimuth) * Math.cos(elevation) * distance
  ];
  const forward = normalize3(subtract3(center, position));
  let right = normalize3(cross3(forward, [0, 1, 0]));
  if (length3(right) < 1e-6) right = [1, 0, 0];
  const up = normalize3(cross3(right, forward));
  return { center, sceneRadius, position, forward, right, up };
}

function shaderSource() {
  return /* wgsl */ `
struct Uniforms {
  centerRadius: vec4<f32>,
  cameraPosition: vec4<f32>,
  cameraRight: vec4<f32>,
  cameraUp: vec4<f32>,
  cameraForward: vec4<f32>,
  viewportAndScale: vec4<f32>,
  options: vec4<f32>,
  reserved: vec4<f32>,
};

struct VertexOut {
  @builtin(position) position: vec4<f32>,
  @location(0) uv: vec2<f32>,
  @location(1) color: vec3<f32>,
  @location(2) opacity: f32,
};

@group(0) @binding(0) var<storage, read> splats: array<f32>;
@group(0) @binding(1) var<uniform> uniforms: Uniforms;

fn readSplat(base: u32, offset: u32) -> f32 { return splats[base + offset]; }

fn shBasis(index: u32, d: vec3<f32>) -> f32 {
  let x = d.x;
  let y = d.y;
  let z = d.z;
  let xx = x * x;
  let yy = y * y;
  let zz = z * z;
  switch index {
    case 0u: { return 0.28209479177387814; }
    case 1u: { return -0.4886025119029199 * y; }
    case 2u: { return 0.4886025119029199 * z; }
    case 3u: { return -0.4886025119029199 * x; }
    case 4u: { return 1.0925484305920792 * x * y; }
    case 5u: { return -1.0925484305920792 * y * z; }
    case 6u: { return 0.31539156525252005 * (2.0 * zz - xx - yy); }
    case 7u: { return -1.0925484305920792 * x * z; }
    case 8u: { return 0.5462742152960396 * (xx - yy); }
    case 9u: { return -0.5900435899266435 * y * (3.0 * xx - yy); }
    case 10u: { return 2.890611442640554 * x * y * z; }
    case 11u: { return -0.4570457994644658 * y * (4.0 * zz - xx - yy); }
    case 12u: { return 0.3731763325901154 * z * (2.0 * zz - 3.0 * xx - 3.0 * yy); }
    case 13u: { return -0.4570457994644658 * x * (4.0 * zz - xx - yy); }
    case 14u: { return 1.445305721320277 * z * (xx - yy); }
    case 15u: { return -0.5900435899266435 * x * (xx - 3.0 * yy); }
    default: { return 0.0; }
  }
}

fn shCoefficient(base: u32, channel: u32, coefficient: u32) -> f32 {
  if (coefficient == 0u) { return readSplat(base, 11u + channel); }
  return readSplat(base, 14u + channel * 15u + coefficient - 1u);
}

fn evaluateColor(base: u32, position: vec3<f32>) -> vec3<f32> {
  if (u32(uniforms.options.w) == 0u) {
    return clamp(vec3<f32>(readSplat(base, 11u), readSplat(base, 12u), readSplat(base, 13u)), vec3<f32>(0.0), vec3<f32>(1.0));
  }
  let direction = normalize(position - uniforms.cameraPosition.xyz);
  var color = vec3<f32>(0.5);
  let coefficientCount = select(1u, 16u, uniforms.reserved.x > 0.5);
  for (var coefficient = 0u; coefficient < coefficientCount; coefficient = coefficient + 1u) {
    let basis = shBasis(coefficient, direction);
    color = color + basis * vec3<f32>(
      shCoefficient(base, 0u, coefficient),
      shCoefficient(base, 1u, coefficient),
      shCoefficient(base, 2u, coefficient)
    );
  }
  return max(color, vec3<f32>(0.0));
}

@vertex
fn vsMain(@builtin(vertex_index) vertexIndex: u32) -> VertexOut {
  let splatIndex = vertexIndex / 6u;
  let local = vertexIndex % 6u;
  let corners = array<vec2<f32>, 6>(
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(-1.0, 1.0),
    vec2<f32>(-1.0, 1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0)
  );
  let corner = corners[local];
  let stride = u32(uniforms.options.z);
  let base = splatIndex * stride;
  let position = vec3<f32>(readSplat(base, 0u), readSplat(base, 1u), readSplat(base, 2u));
  let scaleRadius = max(max(readSplat(base, 3u), readSplat(base, 4u)), readSplat(base, 5u));
  let opacity = readSplat(base, 10u);
  let relative = position - uniforms.centerRadius.xyz;
  let viewX = dot(relative, uniforms.cameraRight.xyz);
  let viewY = dot(relative, uniforms.cameraUp.xyz);
  let viewZ = dot(position - uniforms.cameraPosition.xyz, uniforms.cameraForward.xyz);
  let aspect = uniforms.viewportAndScale.x / max(uniforms.viewportAndScale.y, 1.0);
  let halfHeight = uniforms.centerRadius.w * 1.08;
  let center = vec2<f32>(viewX / (halfHeight * aspect), viewY / halfHeight);
  let distanceFactor = uniforms.centerRadius.w / max(viewZ, uniforms.centerRadius.w * 0.2);
  let radiusPx = clamp(
    scaleRadius * uniforms.viewportAndScale.z * 120.0 * distanceFactor / uniforms.centerRadius.w,
    uniforms.viewportAndScale.w,
    uniforms.options.x
  );
  let ndcRadius = vec2<f32>(radiusPx * 2.0 / uniforms.viewportAndScale.x, radiusPx * 2.0 / uniforms.viewportAndScale.y);
  var out: VertexOut;
  out.position = vec4<f32>(center + corner * ndcRadius, 0.5, 1.0);
  out.uv = corner;
  out.color = evaluateColor(base, position);
  out.opacity = opacity * uniforms.options.y;
  return out;
}

@fragment
fn fsMain(input: VertexOut) -> @location(0) vec4<f32> {
  let r2 = dot(input.uv, input.uv);
  if (r2 > 1.0) { discard; }
  let alpha = clamp(input.opacity * (1.0 - r2), 0.0, 1.0);
  return vec4<f32>(input.color * alpha, alpha);
}
`;
}

function renderManifestStats() {
  els.sampleName.textContent = app.scene.scene?.name || "-";
  els.lodMode.textContent = app.scene.converter?.lodMode || app.scene.asset?.lodMode || "replacement";
  els.codecProfile.textContent = app.profile.id;
  els.shDegree.textContent = String(app.profile.shDegree);
  els.nodeCount.textContent = String(app.nodesDoc.nodes.length);
  renderRuntimeStats();
}

function renderRuntimeStats(frameMs = null) {
  els.chunkCount.textContent = `${app.loadedChunkIds.size} / ${app.chunkById.size}`;
  els.activeChunkCount.textContent = String(app.activeChunkIds.size);
  els.splatCount.textContent = formatInteger(app.renderer?.splatCount || 0);
  els.gpuBytes.textContent = formatBytes(app.renderer?.gpuBufferBytes || 0);
  if (frameMs !== null) {
    const fps = frameMs > 0 ? 1000 / frameMs : 0;
    els.frameTime.textContent = `${frameMs.toFixed(1)} ms / ${fps.toFixed(0)} FPS`;
  }
}

function frameLoop(now) {
  const dt = now - app.lastFrameAt;
  app.lastFrameAt = now;
  if (els.autoOrbit.checked) {
    const next = (Number(els.cameraAzimuth.value) + dt * 0.015) % 360;
    els.cameraAzimuth.value = String(next);
    updateCameraUi();
  }
  app.renderer?.render();
  renderRuntimeStats(dt);
  requestAnimationFrame(frameLoop);
}

function updateCameraUi() {
  els.cameraAzimuthValue.textContent = `${Math.round(Number(els.cameraAzimuth.value))} deg`;
  app.renderer?.render();
}

function setStatus(text, isError = false) {
  els.statusPill.textContent = text;
  els.statusPill.classList.toggle("error", isError);
}

function setControlsEnabled(enabled) {
  for (const element of [els.loadStartup, els.loadLeaves, els.loadAll, els.clear, els.pointScale, els.opacityBoost, els.cameraAzimuth, els.autoOrbit, els.fullSh3]) {
    element.disabled = !enabled;
  }
  if (enabled && app.profile?.shDegree === 0) els.fullSh3.disabled = true;
}

function setShMode(mode) {
  app.shMode = mode === "dc" ? "dc" : "full";
  els.fullSh3.checked = app.shMode === "full";
  app.renderer?.render();
}

function log(message) {
  const time = new Date().toLocaleTimeString();
  els.log.textContent += `[${time}] ${message}\n`;
  els.log.scrollTop = els.log.scrollHeight;
}

function ensureTrailingSlash(value) { return value.endsWith("/") ? value : `${value}/`; }
function subtract3(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function cross3(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function length3(value) { return Math.hypot(value[0], value[1], value[2]); }
function normalize3(value) {
  const length = length3(value);
  return length > 1e-12 ? value.map((component) => component / length) : [0, 0, 1];
}
function formatBytes(bytes) { return bytes ? `${(bytes / 1048576).toFixed(2)} MB` : "0 MB"; }
function formatInteger(value) { return new Intl.NumberFormat("en-US").format(value); }

window.w3gsViewerDebug = {
  loadStartup: () => loadChunkSet(startupChunkIds(), "startup"),
  loadLeaves: () => loadChunkSet(leafChunkIds(), "leaf chunks"),
  loadAll: () => loadChunkSet([...app.chunkById.keys()], "all chunks"),
  setAzimuth: (degrees) => {
    els.cameraAzimuth.value = String(degrees);
    updateCameraUi();
  },
  setShMode,
  verifyShReference: () => app.renderer?.verifyShReference(),
  getState: () => ({
    status: els.statusPill.textContent,
    profile: app.profile?.id || null,
    shDegree: app.profile?.shDegree ?? null,
    loadedChunks: app.loadedChunkIds.size,
    activeChunks: app.activeChunkIds.size,
    activeSplats: app.renderer?.splatCount || 0,
    gpuBytes: app.renderer?.gpuBufferBytes || 0,
    azimuth: Number(els.cameraAzimuth.value),
    shMode: app.shMode
  })
};
