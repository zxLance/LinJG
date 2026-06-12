const MB = 1024 * 1024;
const SAMPLE_SCENE_URL = "../w3gs-format-sample/scene.w3gs.json";

const fallbackScene = {
  durationMs: 16000,
  frameStepMs: 250,
  targetNode: "n3_2",
  rootNodeId: "n0",
  source: {
    label: "Fallback built-in Prototype 0",
    sampleName: "built-in-synthetic",
    nodeCount: 11,
    chunkCount: 34,
    codecList: ["raw-gaussian-v0", "global-raw-v0"],
    loadedFromSample: false
  },
  world: { minX: 0, minY: 0, maxX: 100, maxY: 60 },
  cameraPath: [
    { t: 0, x: 10, y: 45, radius: 34, demand: 0 },
    { t: 3500, x: 28, y: 34, radius: 25, demand: 1 },
    { t: 7600, x: 58, y: 31, radius: 17, demand: 2 },
    { t: 11800, x: 76, y: 20, radius: 11, demand: 3 },
    { t: 16000, x: 82, y: 18, radius: 9, demand: 3 }
  ],
  nodes: [
    node("n0", null, ["n1", "n2", "n3"], [0, 0, 100, 60], [
      layer("n0.base", 0, "base", "c0", "replace-by-children"),
      layer("n0.r1", 1, "refinement", "c1", "additive")
    ], 0.12),
    node("n1", "n0", ["n1_0", "n1_1"], [0, 0, 35, 60], [
      layer("n1.base", 0, "base", "c2", "replace-by-children"),
      layer("n1.r1", 1, "refinement", "c3", "additive"),
      layer("n1.r2", 2, "refinement", "c4", "additive")
    ], 0.09),
    node("n2", "n0", ["n2_0", "n2_1"], [35, 0, 68, 60], [
      layer("n2.base", 0, "base", "c5", "replace-by-children"),
      layer("n2.r1", 1, "refinement", "c6", "additive"),
      layer("n2.r2", 2, "refinement", "c7", "additive")
    ], 0.08),
    node("n3", "n0", ["n3_0", "n3_1", "n3_2"], [68, 0, 100, 60], [
      layer("n3.base", 0, "base", "c8", "replace-by-children"),
      layer("n3.r1", 1, "refinement", "c9", "additive"),
      layer("n3.r2", 2, "refinement", "c10", "additive")
    ], 0.07),
    node("n1_0", "n1", [], [0, 0, 18, 30], [
      layer("n1_0.base", 0, "base", "c11", "additive"),
      layer("n1_0.r1", 1, "refinement", "c12", "additive")
    ], 0.05),
    node("n1_1", "n1", [], [0, 30, 35, 60], [
      layer("n1_1.base", 0, "base", "c13", "additive"),
      layer("n1_1.r1", 1, "refinement", "c14", "additive")
    ], 0.05),
    node("n2_0", "n2", [], [35, 0, 52, 60], [
      layer("n2_0.base", 0, "base", "c15", "additive"),
      layer("n2_0.r1", 1, "refinement", "c16", "additive"),
      layer("n2_0.r2", 2, "refinement", "c17", "additive")
    ], 0.045),
    node("n2_1", "n2", [], [52, 0, 68, 60], [
      layer("n2_1.base", 0, "base", "c18", "additive"),
      layer("n2_1.r1", 1, "refinement", "c19", "additive"),
      layer("n2_1.r2", 2, "refinement", "c20", "additive")
    ], 0.04),
    node("n3_0", "n3", [], [68, 30, 100, 60], [
      layer("n3_0.base", 0, "base", "c21", "additive"),
      layer("n3_0.r1", 1, "refinement", "c22", "additive")
    ], 0.04),
    node("n3_1", "n3", [], [68, 0, 84, 30], [
      layer("n3_1.base", 0, "base", "c23", "additive"),
      layer("n3_1.r1", 1, "refinement", "c24", "additive"),
      layer("n3_1.r2", 2, "refinement", "c25", "additive")
    ], 0.035),
    node("n3_2", "n3", [], [84, 0, 100, 30], [
      layer("n3_2.base", 0, "base", "c26", "additive"),
      layer("n3_2.r1", 1, "refinement", "c27", "additive"),
      layer("n3_2.r2", 2, "refinement", "c28", "additive"),
      layer("n3_2.r3", 3, "refinement", "c29", "additive")
    ], 0.03)
  ],
  chunks: [
    chunk("c0", "n0", 0, 0.65, 12000, 0.9, 0.7),
    chunk("c1", "n0", 1, 1.3, 26000, 1.3, 1.1),
    chunk("c2", "n1", 0, 0.7, 9000, 0.8, 0.75),
    chunk("c3", "n1", 1, 1.8, 26000, 1.4, 1.3),
    chunk("c4", "n1", 2, 4.4, 72000, 2.5, 2.2),
    chunk("c5", "n2", 0, 0.85, 11000, 0.9, 0.85),
    chunk("c6", "n2", 1, 2.1, 32000, 1.6, 1.5),
    chunk("c7", "n2", 2, 5.1, 85000, 2.8, 2.6),
    chunk("c8", "n3", 0, 0.8, 10500, 0.9, 0.8),
    chunk("c9", "n3", 1, 1.9, 28000, 1.5, 1.4),
    chunk("c10", "n3", 2, 4.7, 78000, 2.7, 2.4),
    chunk("c11", "n1_0", 0, 0.55, 7000, 0.7, 0.55),
    chunk("c12", "n1_0", 1, 2.2, 36000, 1.7, 1.4),
    chunk("c13", "n1_1", 0, 0.75, 9600, 0.8, 0.75),
    chunk("c14", "n1_1", 1, 3.4, 59000, 2.1, 1.9),
    chunk("c15", "n2_0", 0, 0.62, 8200, 0.75, 0.65),
    chunk("c16", "n2_0", 1, 2.7, 45000, 1.9, 1.6),
    chunk("c17", "n2_0", 2, 6.2, 104000, 3.2, 2.8),
    chunk("c18", "n2_1", 0, 0.6, 7600, 0.75, 0.6),
    chunk("c19", "n2_1", 1, 2.5, 41000, 1.8, 1.5),
    chunk("c20", "n2_1", 2, 5.9, 97000, 3.0, 2.7),
    chunk("c21", "n3_0", 0, 0.72, 9200, 0.8, 0.7),
    chunk("c22", "n3_0", 1, 3.1, 54000, 2.0, 1.8),
    chunk("c23", "n3_1", 0, 0.58, 7500, 0.75, 0.6),
    chunk("c24", "n3_1", 1, 2.9, 48000, 1.9, 1.7),
    chunk("c25", "n3_1", 2, 6.8, 111000, 3.4, 3.0),
    chunk("c26", "n3_2", 0, 0.52, 6800, 0.7, 0.55),
    chunk("c27", "n3_2", 1, 2.6, 43000, 1.8, 1.6),
    chunk("c28", "n3_2", 2, 6.4, 106000, 3.3, 2.9),
    chunk("c29", "n3_2", 3, 9.4, 155000, 4.1, 3.8),
    chunk("g0", "global", 0, 1.1, 16000, 1.0, 1.0),
    chunk("g1", "global", 1, 6.2, 110000, 2.7, 2.9),
    chunk("g2", "global", 2, 14.5, 250000, 4.8, 5.8),
    chunk("g3", "global", 3, 24.0, 390000, 7.2, 9.2)
  ],
  startupChunkIds: ["c0"],
  progressiveChunkIds: ["g0", "g1", "g2", "g3"]
};

let scene = fallbackScene;
let nodeMap = new Map();
let layerMap = new Map();
let chunkMap = new Map();

function node(id, parent, children, bounds, layers, error) {
  return { id, parent, children, bounds, layers, error };
}

function layer(id, level, kind, chunkId, refinementMode) {
  return { id, level, kind, chunkId, refinementMode };
}

function chunk(id, nodeId, level, sizeMB, splats, decodeCost, gpuMB) {
  return {
    id,
    nodeId,
    level,
    byteLength: Math.round(sizeMB * MB),
    splats,
    decodeCost,
    gpuBytes: Math.round(gpuMB * MB),
    codec: id.startsWith("g") ? "global-raw-v0" : "raw-gaussian-v0"
  };
}

const state = {
  animation: null,
  lastRun: null,
  comparison: []
};

const els = {
  canvas: document.getElementById("sceneCanvas"),
  status: document.getElementById("runStatus"),
  time: document.getElementById("timeLabel"),
  log: document.getElementById("eventLog"),
  comparisonBody: document.getElementById("comparisonBody"),
  strategy: document.getElementById("strategySelect"),
  bandwidth: document.getElementById("bandwidthSelect"),
  latency: document.getElementById("latencySelect"),
  budget: document.getElementById("budgetSelect"),
  runOne: document.getElementById("runOneButton"),
  runAll: document.getElementById("runAllButton"),
  reset: document.getElementById("resetButton"),
  sampleSource: document.getElementById("sampleSource"),
  sampleName: document.getElementById("sampleName"),
  sampleNodes: document.getElementById("sampleNodes"),
  sampleChunks: document.getElementById("sampleChunks"),
  sampleCodecs: document.getElementById("sampleCodecs"),
  first: document.getElementById("metricFirst"),
  bytes: document.getElementById("metricBytes"),
  requests: document.getElementById("metricRequests"),
  overfetch: document.getElementById("metricOverfetch"),
  detail: document.getElementById("metricDetail"),
  gpu: document.getElementById("metricGpu")
};

els.runOne.addEventListener("click", () => {
  runAndRender(els.strategy.value);
});

els.runAll.addEventListener("click", () => {
  const strategies = ["full", "spatial", "progressive", "w3gs"];
  state.comparison = strategies.map((strategy) => simulate(strategy, readNetwork()));
  renderComparison();
  state.lastRun = state.comparison[state.comparison.length - 1];
  animateRun(state.lastRun);
});

els.reset.addEventListener("click", () => {
  if (state.animation) cancelAnimationFrame(state.animation);
  state.lastRun = null;
  state.comparison = [];
  renderEmpty();
  drawScene(null);
});

async function initialize() {
  setControlsEnabled(false);
  els.status.textContent = "Loading W3GS sample";
  renderEmpty();

  try {
    scene = await loadW3gsSample();
  } catch (error) {
    console.warn("Failed to load W3GS sample; using fallback scene.", error);
    scene = fallbackScene;
    scene.source.loadError = error.message;
  }

  rebuildMaps(scene);
  renderSampleInfo();
  renderEmpty();
  drawScene(null);
  setControlsEnabled(true);
}

async function loadW3gsSample() {
  const sceneMeta = await fetchJson(SAMPLE_SCENE_URL);
  const sceneUrl = new URL(SAMPLE_SCENE_URL, window.location.href);
  const nodesDoc = await fetchJson(new URL(sceneMeta.files.nodes, sceneUrl).href);
  const chunksDoc = await fetchJson(new URL(sceneMeta.files.chunks, sceneUrl).href);
  return convertW3gsSample(sceneMeta, nodesDoc, chunksDoc);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  return response.json();
}

function convertW3gsSample(sceneMeta, nodesDoc, chunksDoc) {
  const rawChunks = chunksDoc.chunks || [];
  const rawChunkMap = new Map(rawChunks.map((c) => [c.id, c]));
  const rootNodeId = sceneMeta.entry?.rootNode || nodesDoc.tree?.root || "root";
  const world = worldFromBounds(sceneMeta.bounds);
  const runtimeNodes = nodesDoc.nodes.map((rawNode) => convertNode(rawNode, rawChunkMap));
  const runtimeChunks = rawChunks.map(convertChunk);
  const progressiveChunks = buildProgressiveBaseline(runtimeChunks);
  const targetNode = chooseTargetNode(runtimeNodes);

  return {
    durationMs: 16000,
    frameStepMs: 250,
    targetNode,
    rootNodeId,
    source: {
      label: "W3GS sample JSON",
      sampleName: sceneMeta.scene?.name || "unnamed W3GS sample",
      nodeCount: runtimeNodes.length,
      chunkCount: runtimeChunks.length,
      codecList: (sceneMeta.codecs || []).map((c) => c.id),
      loadedFromSample: true,
      sceneUrl: SAMPLE_SCENE_URL,
      progressiveBaseline: "constructed from all level 0/1/2 node layers"
    },
    world,
    cameraPath: buildCameraPath(world),
    nodes: runtimeNodes,
    chunks: [...runtimeChunks, ...progressiveChunks],
    startupChunkIds: startupChunks(sceneMeta, runtimeNodes),
    progressiveChunkIds: progressiveChunks.map((c) => c.id)
  };
}

function convertNode(rawNode, rawChunkMap) {
  const layers = rawNode.layers.map((rawLayer) => {
    const rawChunk = rawChunkMap.get(rawLayer.chunk);
    return {
      id: rawLayer.id,
      level: rawLayer.level,
      kind: rawLayer.kind,
      chunkId: rawLayer.chunk,
      refinementMode: rawLayer.refinementMode,
      splats: rawLayer.splatCount,
      codec: rawChunk?.codec
    };
  });

  return {
    id: rawNode.id,
    parent: rawNode.parent,
    children: rawNode.children || [],
    bounds: boundsToPlane(rawNode.bounds),
    bounds3d: rawNode.bounds,
    layers,
    error: rawNode.lod?.estimatedError ?? 0,
    priority: rawNode.runtimeHints?.priority ?? 0,
    lod: rawNode.lod,
    runtimeHints: rawNode.runtimeHints
  };
}

function convertChunk(rawChunk) {
  return {
    id: rawChunk.id,
    nodeId: rawChunk.node,
    layerId: rawChunk.layer,
    level: rawChunk.level,
    byteLength: rawChunk.byteLength,
    splats: rawChunk.splatCount,
    decodeCost: rawChunk.runtimeHints?.decodeCost ?? 1,
    gpuBytes: rawChunk.runtimeHints?.gpuUploadBytes ?? rawChunk.byteLength,
    codec: rawChunk.codec || "raw-gaussian-v0",
    uri: rawChunk.uri,
    byteOffset: rawChunk.byteOffset,
    dependencies: rawChunk.dependencies || [],
    priority: rawChunk.runtimeHints?.priority ?? 0,
    attributeSchema: rawChunk.attributeSchema
  };
}

function boundsToPlane(bounds) {
  const min = bounds.min;
  const max = bounds.max;
  return [min[0], min[2], max[0], max[2]];
}

function worldFromBounds(bounds) {
  const [minX, minY, maxX, maxY] = boundsToPlane(bounds);
  const padX = Math.max(0.5, (maxX - minX) * 0.06);
  const padY = Math.max(0.5, (maxY - minY) * 0.06);
  return { minX: minX - padX, minY: minY - padY, maxX: maxX + padX, maxY: maxY + padY };
}

function buildCameraPath(world) {
  const width = world.maxX - world.minX;
  const height = world.maxY - world.minY;
  const radius = Math.max(width, height);
  return [
    { t: 0, x: world.minX + width * 0.18, y: world.maxY - height * 0.18, radius: radius * 0.62, demand: 0 },
    { t: 3500, x: world.minX + width * 0.36, y: world.maxY - height * 0.36, radius: radius * 0.46, demand: 1 },
    { t: 7600, x: world.minX + width * 0.52, y: world.minY + height * 0.44, radius: radius * 0.34, demand: 2 },
    { t: 11800, x: world.minX + width * 0.31, y: world.minY + height * 0.32, radius: radius * 0.25, demand: 3 },
    { t: 16000, x: world.minX + width * 0.27, y: world.minY + height * 0.3, radius: radius * 0.2, demand: 3 }
  ];
}

function chooseTargetNode(nodes) {
  return [...nodes]
    .sort((a, b) => {
      const levelDelta = maxLayer(b) - maxLayer(a);
      if (levelDelta) return levelDelta;
      return (b.priority || 0) - (a.priority || 0);
    })[0]?.id || nodes[0]?.id;
}

function startupChunks(sceneMeta, nodes) {
  const startupSet = new Set(sceneMeta.entry?.startupSet || []);
  const startupIds = [];
  for (const n of nodes) {
    for (const l of n.layers) {
      if (startupSet.has(l.id)) startupIds.push(l.chunkId);
    }
  }
  if (startupIds.length) return startupIds;
  const root = nodes.find((n) => n.id === (sceneMeta.entry?.rootNode || "root"));
  return root?.layers.slice(0, 1).map((l) => l.chunkId) || [];
}

function buildProgressiveBaseline(realChunks) {
  const levels = [0, 1, 2];
  return levels.map((level) => {
    const group = realChunks.filter((c) => c.level === level);
    return {
      id: `progressive.level${level}`,
      nodeId: "global",
      layerId: `global.progressive.${level}`,
      level,
      byteLength: group.reduce((sum, c) => sum + c.byteLength, 0),
      splats: group.reduce((sum, c) => sum + c.splats, 0),
      decodeCost: group.length ? group.reduce((sum, c) => sum + c.decodeCost, 0) / group.length : 1,
      gpuBytes: group.reduce((sum, c) => sum + c.gpuBytes, 0),
      codec: "progressive-baseline-from-sample-layers",
      syntheticProgressive: true
    };
  }).filter((c) => c.byteLength > 0);
}

function rebuildMaps(nextScene) {
  nodeMap = new Map(nextScene.nodes.map((n) => [n.id, n]));
  chunkMap = new Map(nextScene.chunks.map((c) => [c.id, c]));
  layerMap = new Map();
  for (const n of nextScene.nodes) {
    for (const l of n.layers) layerMap.set(l.id, { ...l, nodeId: n.id });
  }
}

function setControlsEnabled(enabled) {
  for (const el of [els.runOne, els.runAll, els.reset, els.strategy, els.bandwidth, els.latency, els.budget]) {
    el.disabled = !enabled;
  }
}

function readNetwork() {
  return {
    bandwidthBytesPerMs: (Number(els.bandwidth.value) * MB) / 1000,
    latencyMs: Number(els.latency.value),
    gpuBudgetBytes: Number(els.budget.value) * MB
  };
}

function runAndRender(strategy) {
  const result = simulate(strategy, readNetwork());
  state.lastRun = result;
  state.comparison = [result];
  renderComparison();
  animateRun(result);
}

function simulate(strategy, network) {
  const loaded = new Set();
  const requested = new Map();
  const requestEvents = [];
  const loadedEvents = [];
  const frames = [];
  const usedChunks = new Set();
  const targetDetailChunk = targetDetailChunkId();
  const targetNearDetailChunk = targetNearDetailChunkId();
  let firstRenderMs = null;
  let localDetailMs = null;
  let peakGpuBytes = 0;
  let qualityArea = 0;

  for (let t = 0; t <= scene.durationMs; t += scene.frameStepMs) {
    finishRequests(t, requested, loaded, loadedEvents);
    const camera = interpolateCamera(t);
    const visibleNodes = visibleLeafOrMidNodes(camera);
    const desired = desiredChunks(strategy, camera, visibleNodes, loaded);
    issueRequests(t, desired, requested, loaded, requestEvents, network);
    finishRequests(t, requested, loaded, loadedEvents);

    const visibleQuality = estimateVisibleQuality(visibleNodes, loaded);
    const visibleSplats = estimateVisibleSplats(visibleNodes, loaded);
    const visibleLoaded = visibleSplats > 0;
    if (firstRenderMs === null && visibleLoaded) firstRenderMs = t;
    if (localDetailMs === null && targetDetailChunk && targetNearDetailChunk && loaded.has(targetNearDetailChunk)) {
      localDetailMs = t;
    }

    for (const n of visibleNodes) {
      for (const layerInfo of n.layers) {
        if (loaded.has(layerInfo.chunkId)) usedChunks.add(layerInfo.chunkId);
      }
    }
    if (strategy === "progressive") {
      for (const id of loaded) if (chunkMap.get(id)?.syntheticProgressive || id.startsWith("g")) usedChunks.add(id);
    }

    const gpuBytes = [...loaded].reduce((sum, id) => sum + (chunkMap.get(id)?.gpuBytes || 0), 0);
    peakGpuBytes = Math.max(peakGpuBytes, gpuBytes);
    qualityArea += visibleQuality * scene.frameStepMs;

    frames.push({
      t,
      camera,
      visibleNodeIds: visibleNodes.map((n) => n.id),
      loaded: new Set(loaded),
      visibleQuality,
      visibleSplats,
      gpuBytes
    });
  }

  const downloadedBytes = [...loaded].reduce((sum, id) => sum + (chunkMap.get(id)?.byteLength || 0), 0);
  const overfetchBytes = [...loaded].reduce((sum, id) => {
    const c = chunkMap.get(id);
    if (!c) return sum;
    if (strategy === "full") return usedChunks.has(id) ? sum : sum + c.byteLength;
    if (strategy === "progressive") return sum + c.byteLength * 0.35;
    return usedChunks.has(id) ? sum : sum + c.byteLength;
  }, 0);

  return {
    strategy,
    frames,
    requestEvents,
    loadedEvents,
    firstRenderMs,
    localDetailMs,
    downloadedBytes,
    requests: requestEvents.length,
    overfetchRatio: downloadedBytes ? overfetchBytes / downloadedBytes : 0,
    peakGpuBytes,
    qualityArea,
    network
  };
}

function finishRequests(t, requested, loaded, loadedEvents) {
  for (const [id, req] of [...requested.entries()]) {
    if (req.finish <= t) {
      requested.delete(id);
      loaded.add(id);
      loadedEvents.push({ t, id });
    }
  }
}

function issueRequests(t, desired, requested, loaded, requestEvents, network) {
  const sorted = [...desired]
    .filter((id) => !loaded.has(id) && !requested.has(id))
    .map((id) => chunkMap.get(id))
    .filter(Boolean)
    .sort((a, b) => requestScore(a) - requestScore(b));

  for (const c of sorted.slice(0, 4)) {
    const transfer = c.byteLength / network.bandwidthBytesPerMs;
    const decode = c.decodeCost * 35;
    const finish = t + network.latencyMs + transfer + decode;
    requested.set(c.id, { start: t, finish });
    requestEvents.push({ t, id: c.id, finish });
  }
}

function requestScore(c) {
  const priority = c.priority ? (100 - c.priority) / 20 : 0;
  return c.level * 10 + c.decodeCost + c.byteLength / MB + priority;
}

function desiredChunks(strategy, camera, visibleNodes, loaded) {
  if (strategy === "full") {
    return new Set(scene.chunks.filter((c) => !isProgressiveChunk(c)).map((c) => c.id));
  }

  if (strategy === "progressive") {
    const maxLevel = Math.max(0, Math.min(2, camera.demand));
    return new Set((scene.progressiveChunkIds || [])
      .map((id) => chunkMap.get(id))
      .filter((c) => c && c.level <= maxLevel)
      .map((c) => c.id));
  }

  if (strategy === "spatial") {
    const ids = new Set();
    for (const n of visibleNodes) {
      const maxLevel = Math.min(maxLayer(n), Math.max(1, camera.demand));
      for (const l of n.layers) {
        if (l.level <= maxLevel) ids.add(l.chunkId);
      }
    }
    return ids;
  }

  const ids = new Set(scene.startupChunkIds || []);
  for (const n of visibleNodes) {
    const demand = Math.min(maxLayer(n), camera.demand);
    const loadedLevels = n.layers.filter((l) => loaded.has(l.chunkId)).map((l) => l.level);
    const nextLevel = loadedLevels.length ? Math.min(demand, Math.max(...loadedLevels) + 1) : 0;
    for (const l of n.layers) {
      if (l.level <= nextLevel) ids.add(l.chunkId);
    }
  }
  return ids;
}

function isProgressiveChunk(chunkInfo) {
  return chunkInfo.syntheticProgressive || chunkInfo.id.startsWith("g");
}

function maxLayer(nodeInfo) {
  return Math.max(...nodeInfo.layers.map((l) => l.level));
}

function visibleLeafOrMidNodes(camera) {
  const root = nodeMap.get(scene.rootNodeId);
  const candidates = camera.demand >= 2
    ? scene.nodes.filter((n) => n.children.length === 0)
    : scene.nodes.filter((n) => n.id === scene.rootNodeId || n.parent === root?.id);
  return candidates.filter((n) => intersectsCamera(n.bounds, camera));
}

function intersectsCamera(bounds, camera) {
  const [minX, minY, maxX, maxY] = bounds;
  const x = Math.max(minX, Math.min(camera.x, maxX));
  const y = Math.max(minY, Math.min(camera.y, maxY));
  const dx = x - camera.x;
  const dy = y - camera.y;
  return dx * dx + dy * dy <= camera.radius * camera.radius;
}

function estimateVisibleQuality(visibleNodes, loaded) {
  if (!visibleNodes.length) return 0;
  if (hasLoadedProgressive(loaded)) return estimateProgressiveQuality(loaded);
  let total = 0;
  for (const n of visibleNodes) {
    const max = Math.max(1, maxLayer(n));
    const loadedMax = Math.max(-1, ...n.layers.filter((l) => loaded.has(l.chunkId)).map((l) => l.level));
    total += loadedMax < 0 ? 0 : (loadedMax + 1) / (max + 1);
  }
  return total / visibleNodes.length;
}

function estimateProgressiveQuality(loaded) {
  const levels = [...loaded]
    .map((id) => chunkMap.get(id))
    .filter((c) => c && isProgressiveChunk(c))
    .map((c) => c.level);
  const maxLoaded = levels.length ? Math.max(...levels) : -1;
  return maxLoaded < 0 ? 0 : (maxLoaded + 1) / 3;
}

function hasLoadedProgressive(loaded) {
  return [...loaded].some((id) => {
    const c = chunkMap.get(id);
    return c && isProgressiveChunk(c);
  });
}

function estimateVisibleSplats(visibleNodes, loaded) {
  let splats = 0;
  for (const n of visibleNodes) {
    for (const l of n.layers) {
      if (loaded.has(l.chunkId)) splats += chunkMap.get(l.chunkId).splats;
    }
  }
  for (const id of loaded) {
    const c = chunkMap.get(id);
    if (c && isProgressiveChunk(c)) splats += c.splats * 0.25;
  }
  return Math.round(splats);
}

function targetDetailChunkId() {
  const target = nodeMap.get(scene.targetNode);
  if (!target) return null;
  return [...target.layers].sort((a, b) => b.level - a.level)[0]?.chunkId || null;
}

function targetNearDetailChunkId() {
  const target = nodeMap.get(scene.targetNode);
  if (!target) return null;
  const layers = [...target.layers].sort((a, b) => b.level - a.level);
  return layers[1]?.chunkId || layers[0]?.chunkId || null;
}

function interpolateCamera(t) {
  const path = scene.cameraPath;
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    if (t >= a.t && t <= b.t) {
      const u = (t - a.t) / (b.t - a.t);
      return {
        x: lerp(a.x, b.x, u),
        y: lerp(a.y, b.y, u),
        radius: lerp(a.radius, b.radius, u),
        demand: Math.round(lerp(a.demand, b.demand, u))
      };
    }
  }
  return path[path.length - 1];
}

function lerp(a, b, u) {
  return a + (b - a) * u;
}

function animateRun(result) {
  if (state.animation) cancelAnimationFrame(state.animation);
  els.status.textContent = strategyLabel(result.strategy);
  renderMetrics(result);
  renderLog(result);
  const started = performance.now();

  function tick(now) {
    const elapsed = ((now - started) * 2.2) % scene.durationMs;
    const frame = nearestFrame(result.frames, elapsed);
    drawScene(frame);
    els.time.textContent = `t = ${Math.round(frame.t)} ms`;
    state.animation = requestAnimationFrame(tick);
  }

  state.animation = requestAnimationFrame(tick);
}

function nearestFrame(frames, t) {
  let best = frames[0];
  for (const f of frames) {
    if (Math.abs(f.t - t) < Math.abs(best.t - t)) best = f;
  }
  return best;
}

function drawScene(frame) {
  const ctx = els.canvas.getContext("2d");
  const w = els.canvas.width;
  const h = els.canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#fbfcff";
  ctx.fillRect(0, 0, w, h);
  drawGrid(ctx, w, h);

  for (const n of scene.nodes) {
    if (n.id === scene.rootNodeId) continue;
    const rect = project(n.bounds, w, h);
    const loadedLevel = frame ? loadedLevelForNode(n, frame.loaded) : -1;
    ctx.fillStyle = loadedLevel >= 0 ? colorForLevel(loadedLevel) : "#ffffff";
    ctx.strokeStyle = n.children.length ? "#7d8ca3" : "#b7c1d1";
    ctx.lineWidth = n.children.length ? 2 : 1;
    ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
    ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
    ctx.fillStyle = "#334155";
    ctx.font = "13px Segoe UI, Arial";
    ctx.fillText(`${n.id}${loadedLevel >= 0 ? ` L${loadedLevel}` : ""}`, rect.x + 8, rect.y + 20);
  }

  if (frame) {
    const c = projectPoint(frame.camera.x, frame.camera.y, w, h);
    const r = frame.camera.radius * (w / (scene.world.maxX - scene.world.minX));
    ctx.beginPath();
    ctx.arc(c.x, c.y, r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(37, 99, 235, 0.08)";
    ctx.fill();
    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(c.x, c.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#1d4ed8";
    ctx.fill();
  }

  drawLegend(ctx, w, h);
}

function drawGrid(ctx, w, h) {
  ctx.strokeStyle = "#edf1f7";
  ctx.lineWidth = 1;
  for (let x = 0; x <= w; x += w / 10) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y <= h; y += h / 6) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
}

function drawLegend(ctx, w, h) {
  const items = [
    ["not loaded", "#ffffff"],
    ["base", "#dbeafe"],
    ["r1", "#bfdbfe"],
    ["r2", "#93c5fd"],
    ["r3", "#60a5fa"]
  ];
  let x = 18;
  const y = h - 28;
  ctx.font = "12px Segoe UI, Arial";
  for (const [label, color] of items) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y - 12, 16, 16);
    ctx.strokeStyle = "#94a3b8";
    ctx.strokeRect(x, y - 12, 16, 16);
    ctx.fillStyle = "#475569";
    ctx.fillText(label, x + 22, y + 1);
    x += 105;
  }
}

function loadedLevelForNode(nodeInfo, loaded) {
  const levels = nodeInfo.layers.filter((l) => loaded.has(l.chunkId)).map((l) => l.level);
  return levels.length ? Math.max(...levels) : -1;
}

function colorForLevel(level) {
  return ["#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa"][Math.min(level, 3)];
}

function project(bounds, w, h) {
  const [minX, minY, maxX, maxY] = bounds;
  const p1 = projectPoint(minX, maxY, w, h);
  const p2 = projectPoint(maxX, minY, w, h);
  return { x: p1.x, y: p1.y, w: p2.x - p1.x, h: p2.y - p1.y };
}

function projectPoint(x, y, w, h) {
  const sx = (x - scene.world.minX) / (scene.world.maxX - scene.world.minX);
  const sy = (y - scene.world.minY) / (scene.world.maxY - scene.world.minY);
  return { x: sx * w, y: (1 - sy) * h };
}

function renderMetrics(result) {
  els.first.textContent = formatMs(result.firstRenderMs);
  els.bytes.textContent = formatBytes(result.downloadedBytes);
  els.requests.textContent = String(result.requests);
  els.overfetch.textContent = `${Math.round(result.overfetchRatio * 100)}%`;
  els.detail.textContent = formatMs(result.localDetailMs);
  els.gpu.textContent = formatBytes(result.peakGpuBytes);
}

function renderComparison() {
  els.comparisonBody.innerHTML = "";
  for (const r of state.comparison) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${strategyLabel(r.strategy)}</td>
      <td>${formatMs(r.firstRenderMs)}</td>
      <td>${formatBytes(r.downloadedBytes)}</td>
      <td>${r.requests}</td>
      <td>${Math.round(r.overfetchRatio * 100)}%</td>
      <td>${formatMs(r.localDetailMs)}</td>
      <td>${formatBytes(r.peakGpuBytes)}</td>
      <td>${Math.round(r.qualityArea)}</td>
    `;
    els.comparisonBody.appendChild(row);
  }
}

function renderLog(result) {
  const requestLines = result.requestEvents.slice(0, 42).map((e) => {
    const c = chunkMap.get(e.id);
    return `${String(Math.round(e.t)).padStart(5)} ms  request ${e.id.padEnd(24)} node=${c.nodeId.padEnd(10)} L${c.level} size=${formatBytes(c.byteLength)}`;
  });
  els.log.textContent = requestLines.join("\n");
}

function renderSampleInfo() {
  const source = scene.source || {};
  els.sampleSource.textContent = source.loadedFromSample ? source.label : `${source.label} (${source.loadError || "sample fetch failed"})`;
  els.sampleName.textContent = source.sampleName || "-";
  els.sampleNodes.textContent = String(source.nodeCount ?? scene.nodes.length);
  els.sampleChunks.textContent = `${source.chunkCount ?? scene.chunks.length}`;
  els.sampleCodecs.textContent = source.codecList?.length ? source.codecList.join(", ") : "raw-gaussian-v0";
}

function renderEmpty() {
  els.status.textContent = scene.source?.loadedFromSample ? "Ready: W3GS sample" : "Ready";
  els.time.textContent = "t = 0 ms";
  els.first.textContent = "-";
  els.bytes.textContent = "-";
  els.requests.textContent = "-";
  els.overfetch.textContent = "-";
  els.detail.textContent = "-";
  els.gpu.textContent = "-";
  els.log.textContent = "";
  els.comparisonBody.innerHTML = '<tr><td colspan="8">Run all baselines to fill this table.</td></tr>';
}

function strategyLabel(strategy) {
  return {
    full: "Full loading",
    spatial: "Spatial-only",
    progressive: "Progressive-only",
    w3gs: "W3GS scheduling"
  }[strategy];
}

function formatMs(value) {
  if (value === null || value === undefined) return "-";
  return `${Math.round(value)} ms`;
}

function formatBytes(value) {
  if (!value) return "0 MB";
  return `${(value / MB).toFixed(2)} MB`;
}

rebuildMaps(scene);
renderSampleInfo();
initialize();
