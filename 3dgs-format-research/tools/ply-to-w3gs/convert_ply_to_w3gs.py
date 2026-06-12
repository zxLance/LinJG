#!/usr/bin/env python3
"""Convert a common 3D Gaussian Splatting PLY into a W3GS Prototype 1 sample."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SH_C0 = 0.28209479177387814
MB = 1024 * 1024
RAW_GAUSSIAN_V0_STRUCT = struct.Struct("<3f3f4ff3f")
RAW_GAUSSIAN_SH3_V0_STRUCT = struct.Struct("<59f")
SH3_REST_NAMES = [f"f_rest_{index}" for index in range(45)]


@dataclass(frozen=True)
class PayloadProfile:
    id: str
    schema_id: str
    sh_degree: int
    record_struct: struct.Struct
    attributes: tuple[tuple[str, str, int], ...]
    description: str


PAYLOAD_PROFILES = {
    "raw-gaussian-v0": PayloadProfile(
        id="raw-gaussian-v0",
        schema_id="gaussian-basic-v0",
        sh_degree=0,
        record_struct=RAW_GAUSSIAN_V0_STRUCT,
        attributes=(
            ("position", "float32", 3),
            ("scale", "float32", 3),
            ("rotation", "float32", 4),
            ("opacity", "float32", 1),
            ("color", "float32", 3),
        ),
        description="14 float32 values per splat with activated SH0 color.",
    ),
    "raw-gaussian-sh3-v0": PayloadProfile(
        id="raw-gaussian-sh3-v0",
        schema_id="gaussian-sh3-v0",
        sh_degree=3,
        record_struct=RAW_GAUSSIAN_SH3_V0_STRUCT,
        attributes=(
            ("position", "float32", 3),
            ("scale", "float32", 3),
            ("rotation", "float32", 4),
            ("opacity", "float32", 1),
            ("shDc", "float32", 3),
            ("shRest", "float32", 45),
        ),
        description="59 float32 values per splat with complete degree-3 SH coefficients.",
    ),
}


PLY_SCALAR_TYPES: dict[str, tuple[str, int]] = {
    "char": ("b", 1),
    "uchar": ("B", 1),
    "int8": ("b", 1),
    "uint8": ("B", 1),
    "short": ("h", 2),
    "ushort": ("H", 2),
    "int16": ("h", 2),
    "uint16": ("H", 2),
    "int": ("i", 4),
    "uint": ("I", 4),
    "int32": ("i", 4),
    "uint32": ("I", 4),
    "float": ("f", 4),
    "float32": ("f", 4),
    "double": ("d", 8),
    "float64": ("d", 8),
}


REQUIRED_3DGS_FIELDS = {
    "x",
    "y",
    "z",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
    "rot_0",
    "rot_1",
    "rot_2",
    "rot_3",
}


@dataclass
class PlyProperty:
    name: str
    scalar_type: str


@dataclass
class PlyHeader:
    path: Path
    format: str
    vertex_count: int
    properties: list[PlyProperty]
    comments: list[str]
    header_bytes: int

    @property
    def property_names(self) -> list[str]:
        return [p.name for p in self.properties]

    @property
    def is_3dgs(self) -> bool:
        return REQUIRED_3DGS_FIELDS.issubset(set(self.property_names))

    @property
    def f_rest_count(self) -> int:
        return sum(1 for name in self.property_names if name.startswith("f_rest_"))


@dataclass
class Splat:
    x: float
    y: float
    z: float
    scale: tuple[float, float, float]
    rotation: tuple[float, float, float, float]
    opacity: float
    color: tuple[float, float, float]
    sh_dc: tuple[float, float, float]
    sh_rest: tuple[float, ...]
    importance: float


@dataclass
class RuntimeNode:
    id: str
    parent: str | None
    children: list[str]
    indices: list[int]
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    depth: int


@dataclass
class SummaryResult:
    splats: list[Splat]
    source_splat_count: int
    summary_splat_count: int
    grid_size: tuple[int, int, int]
    approx_error: float
    geometric_error: float


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output)

    header = read_ply_header(input_path)
    print_header_summary(header)
    if args.inspect_only:
        return

    if not header.is_3dgs:
        missing = sorted(REQUIRED_3DGS_FIELDS - set(header.property_names))
        raise SystemExit(f"Input is not a recognized 3DGS PLY; missing fields: {', '.join(missing)}")

    payload_profile = resolve_payload_profile(header, args.payload_profile)
    print(f"Payload profile: {payload_profile.id} ({payload_profile.record_struct.size} bytes/splat)")
    splats, selected = load_splats(header, max_splats=args.max_splats, payload_profile=payload_profile)
    if not splats:
        raise SystemExit("No splats selected from input PLY.")

    nodes = build_octree(
        splats,
        list(range(len(splats))),
        max_depth=args.max_depth,
        max_leaf_splats=args.max_leaf_splats,
    )
    write_w3gs(
        output_dir=output_dir,
        input_path=input_path,
        header=header,
        splats=splats,
        selected_indices=selected,
        nodes=nodes,
        lod_mode=args.lod_mode,
        base_ratio=args.base_ratio,
        min_refinement_splats=args.min_refinement_splats,
        summary_target_ratio=args.summary_target_ratio,
        summary_max_splats=args.summary_max_splats,
        payload_file_max_mb=args.payload_file_max_mb,
        payload_profile=payload_profile,
    )
    print(f"Wrote W3GS sample to: {output_dir.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a common 3DGS PLY into W3GS Prototype 1 scene/nodes/chunks/payload files."
    )
    parser.add_argument("--input", required=True, help="Input 3DGS PLY path.")
    parser.add_argument("--output", required=True, help="Output directory for scene.w3gs.json and related files.")
    parser.add_argument(
        "--max-splats",
        type=int,
        default=200_000,
        help="Maximum number of splats to convert. Default: 200000.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=4,
        help="Maximum octree depth. Default: 4.",
    )
    parser.add_argument(
        "--max-leaf-splats",
        type=int,
        default=25_000,
        help="Split octree nodes larger than this until max depth. Default: 25000.",
    )
    parser.add_argument(
        "--base-ratio",
        type=float,
        default=0.25,
        help="duplicated-parent mode: keep this top-importance ratio in the base layer. Default: 0.25.",
    )
    parser.add_argument(
        "--min-refinement-splats",
        type=int,
        default=8_000,
        help="duplicated-parent mode: nodes below this size get only a base layer. Default: 8000.",
    )
    parser.add_argument(
        "--lod-mode",
        choices=["duplicated-parent", "parent-summary"],
        default="duplicated-parent",
        help="LoD payload generation mode. Default keeps the Prototype 1 baseline: duplicated-parent.",
    )
    parser.add_argument(
        "--summary-target-ratio",
        type=float,
        default=0.08,
        help="parent-summary mode: target summary splats per internal node as a ratio of source splats. Default: 0.08.",
    )
    parser.add_argument(
        "--summary-max-splats",
        type=int,
        default=12_000,
        help="parent-summary mode: cap summary splats per internal node. Default: 12000.",
    )
    parser.add_argument(
        "--payload-profile",
        choices=["auto", "raw-gaussian-v0", "raw-gaussian-sh3-v0"],
        default="auto",
        help="Payload profile. auto selects SH3 for a complete f_rest_0..44 set and errors on partial SH3. Default: auto.",
    )
    parser.add_argument(
        "--payload-file-max-mb",
        type=float,
        default=64,
        help="Roll payload/chunks-*.bin after roughly this size. Default: 64.",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Only print PLY header summary; do not convert.",
    )
    return parser.parse_args()


def read_ply_header(path: Path) -> PlyHeader:
    if not path.exists():
        raise FileNotFoundError(path)

    comments: list[str] = []
    properties: list[PlyProperty] = []
    ply_format: str | None = None
    vertex_count: int | None = None
    in_vertex = False
    header_bytes = 0

    with path.open("rb") as f:
        first = f.readline()
        header_bytes += len(first)
        if first.strip() != b"ply":
            raise ValueError(f"{path} is not a PLY file.")

        while True:
            line_bytes = f.readline()
            if not line_bytes:
                raise ValueError("Unexpected EOF before end_header.")
            header_bytes += len(line_bytes)
            line = line_bytes.decode("ascii", errors="replace").strip()
            if line == "end_header":
                break
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "format":
                ply_format = parts[1]
            elif parts[0] == "comment":
                comments.append(line[len("comment ") :])
            elif parts[0] == "element":
                in_vertex = parts[1] == "vertex"
                if in_vertex:
                    vertex_count = int(parts[2])
            elif parts[0] == "property" and in_vertex:
                if parts[1] == "list":
                    raise ValueError("List properties in vertex elements are not supported.")
                properties.append(PlyProperty(name=parts[2], scalar_type=parts[1]))

    if ply_format is None or vertex_count is None:
        raise ValueError("PLY header is missing format or element vertex.")
    if ply_format not in {"binary_little_endian", "ascii"}:
        raise ValueError(f"Unsupported PLY format: {ply_format}")

    return PlyHeader(path, ply_format, vertex_count, properties, comments, header_bytes)


def print_header_summary(header: PlyHeader) -> None:
    size = header.path.stat().st_size
    present = sorted(REQUIRED_3DGS_FIELDS & set(header.property_names))
    missing = sorted(REQUIRED_3DGS_FIELDS - set(header.property_names))
    print(json.dumps(
        {
            "path": str(header.path),
            "bytes": size,
            "mib": round(size / 1024 / 1024, 2),
            "format": header.format,
            "vertexCount": header.vertex_count,
            "propertyCount": len(header.properties),
            "properties": header.property_names,
            "is3dgsPly": header.is_3dgs,
            "present3dgsFields": present,
            "missing3dgsFields": missing,
            "fRestCount": header.f_rest_count,
        },
        ensure_ascii=False,
        indent=2,
    ))


def resolve_payload_profile(header: PlyHeader, requested: str) -> PayloadProfile:
    present = {name for name in header.property_names if name.startswith("f_rest_")}
    required = set(SH3_REST_NAMES)
    if requested == "raw-gaussian-v0":
        return PAYLOAD_PROFILES[requested]
    if requested == "raw-gaussian-sh3-v0":
        missing = sorted(required - present, key=lambda name: int(name.rsplit("_", 1)[1]))
        unexpected = sorted(present - required)
        if missing or unexpected:
            raise SystemExit(
                "raw-gaussian-sh3-v0 requires exactly f_rest_0..44; "
                f"missing={missing}, unexpected={unexpected}"
            )
        return PAYLOAD_PROFILES[requested]
    if not present:
        return PAYLOAD_PROFILES["raw-gaussian-v0"]
    if present == required:
        return PAYLOAD_PROFILES["raw-gaussian-sh3-v0"]
    missing = sorted(required - present, key=lambda name: int(name.rsplit("_", 1)[1]))
    unexpected = sorted(present - required)
    raise SystemExit(
        "Partial SH3 fields cannot be converted implicitly. Select raw-gaussian-v0 explicitly to downcast, "
        f"or provide exactly f_rest_0..44; missing={missing}, unexpected={unexpected}"
    )


def input_sh_metadata(header: PlyHeader, payload_profile: PayloadProfile) -> dict[str, Any]:
    present = {name for name in header.property_names if name.startswith("f_rest_")}
    if not present:
        state = "sh0"
        degree: int | None = 0
    elif present == set(SH3_REST_NAMES):
        state = "complete-sh3"
        degree = 3
    else:
        state = "partial-or-nonstandard"
        degree = None
    downcast = bool(present) and payload_profile.sh_degree == 0
    return {
        "inputShState": state,
        "inputShDegree": degree,
        "outputShDegree": payload_profile.sh_degree,
        "shDowncast": downcast,
        "ignoredShRestCount": len(present) if downcast else 0,
    }


def load_splats(header: PlyHeader, max_splats: int, payload_profile: PayloadProfile) -> tuple[list[Splat], list[int]]:
    target = min(max_splats, header.vertex_count) if max_splats else header.vertex_count
    selected_indices = select_indices(header.vertex_count, target)
    if header.format == "binary_little_endian":
        return load_binary_splats(header, selected_indices, payload_profile), selected_indices
    return load_ascii_splats(header, set(selected_indices), payload_profile), selected_indices


def select_indices(total: int, target: int) -> list[int]:
    if target >= total:
        return list(range(total))
    indices: list[int] = []
    last = -1
    for i in range(target):
        idx = int(i * total / target)
        if idx != last:
            indices.append(idx)
            last = idx
    return indices


def binary_struct_for(header: PlyHeader) -> tuple[struct.Struct, int]:
    fmt = "<"
    size = 0
    for prop in header.properties:
        if prop.scalar_type not in PLY_SCALAR_TYPES:
            raise ValueError(f"Unsupported scalar property type: {prop.scalar_type}")
        code, bytes_ = PLY_SCALAR_TYPES[prop.scalar_type]
        fmt += code
        size += bytes_
    return struct.Struct(fmt), size


def load_binary_splats(header: PlyHeader, selected_indices: list[int], payload_profile: PayloadProfile) -> list[Splat]:
    record_struct, record_size = binary_struct_for(header)
    names = header.property_names
    splats: list[Splat] = []
    with header.path.open("rb") as f:
        for idx in selected_indices:
            f.seek(header.header_bytes + idx * record_size)
            raw = f.read(record_size)
            if len(raw) != record_size:
                raise ValueError(f"Short read at vertex {idx}.")
            values = dict(zip(names, record_struct.unpack(raw)))
            splats.append(splat_from_values(values, payload_profile))
    return splats


def load_ascii_splats(header: PlyHeader, selected_indices: set[int], payload_profile: PayloadProfile) -> list[Splat]:
    names = header.property_names
    splats: list[Splat] = []
    with header.path.open("r", encoding="ascii", errors="replace") as f:
        for line in f:
            if line.strip() == "end_header":
                break
        for i in range(header.vertex_count):
            line = f.readline()
            if i not in selected_indices:
                continue
            values = dict(zip(names, (float(x) for x in line.split())))
            splats.append(splat_from_values(values, payload_profile))
    return splats


def splat_from_values(values: dict[str, Any], payload_profile: PayloadProfile) -> Splat:
    position = (float(values["x"]), float(values["y"]), float(values["z"]))
    raw_scale = (float(values["scale_0"]), float(values["scale_1"]), float(values["scale_2"]))
    scale = tuple(safe_exp(v) for v in raw_scale)
    rotation = normalize_quat((
        float(values["rot_0"]),
        float(values["rot_1"]),
        float(values["rot_2"]),
        float(values["rot_3"]),
    ))
    opacity = sigmoid(float(values["opacity"]))
    sh_dc = tuple(float(values[f"f_dc_{i}"]) for i in range(3))
    color = tuple(clamp01(0.5 + SH_C0 * value) for value in sh_dc)
    sh_rest = tuple(float(values[name]) for name in SH3_REST_NAMES) if payload_profile.sh_degree == 3 else ()
    importance = opacity * max(scale)
    return Splat(position[0], position[1], position[2], scale, rotation, opacity, color, sh_dc, sh_rest, importance)


def safe_exp(value: float) -> float:
    return math.exp(max(-20.0, min(20.0, value)))


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def normalize_quat(values: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    length = math.sqrt(sum(v * v for v in values))
    if length <= 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    return tuple(v / length for v in values)  # type: ignore[return-value]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def build_octree(
    splats: list[Splat],
    indices: list[int],
    max_depth: int,
    max_leaf_splats: int,
) -> list[RuntimeNode]:
    nodes: list[RuntimeNode] = []

    def create(node_id: str, parent: str | None, node_indices: list[int], depth: int) -> str:
        bounds_min, bounds_max = bounds_for(splats, node_indices)
        runtime = RuntimeNode(node_id, parent, [], node_indices, bounds_min, bounds_max, depth)
        nodes.append(runtime)
        if depth >= max_depth or len(node_indices) <= max_leaf_splats:
            return node_id

        center = tuple((bounds_min[i] + bounds_max[i]) * 0.5 for i in range(3))
        buckets: list[list[int]] = [[] for _ in range(8)]
        for idx in node_indices:
            s = splats[idx]
            octant = (1 if s.x >= center[0] else 0) | (2 if s.y >= center[1] else 0) | (4 if s.z >= center[2] else 0)
            buckets[octant].append(idx)

        for octant, bucket in enumerate(buckets):
            if not bucket:
                continue
            child_id = f"{node_id}_{octant}"
            runtime.children.append(child_id)
            create(child_id, node_id, bucket, depth + 1)
        return node_id

    create("root", None, indices, 0)
    return nodes


def bounds_for(splats: list[Splat], indices: Iterable[int]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    iterator = iter(indices)
    first = next(iterator)
    first_splat = splats[first]
    min_v = [first_splat.x, first_splat.y, first_splat.z]
    max_v = [first_splat.x, first_splat.y, first_splat.z]
    for idx in iterator:
        s = splats[idx]
        min_v[0] = min(min_v[0], s.x)
        min_v[1] = min(min_v[1], s.y)
        min_v[2] = min(min_v[2], s.z)
        max_v[0] = max(max_v[0], s.x)
        max_v[1] = max(max_v[1], s.y)
        max_v[2] = max(max_v[2], s.z)
    return tuple(min_v), tuple(max_v)  # type: ignore[return-value]


def write_w3gs(
    output_dir: Path,
    input_path: Path,
    header: PlyHeader,
    splats: list[Splat],
    selected_indices: list[int],
    nodes: list[RuntimeNode],
    lod_mode: str,
    base_ratio: float,
    min_refinement_splats: int,
    summary_target_ratio: float,
    summary_max_splats: int,
    payload_file_max_mb: float,
    payload_profile: PayloadProfile,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_dir = output_dir / "payload"
    payload_dir.mkdir(parents=True, exist_ok=True)
    for stale in payload_dir.glob("chunks-*.bin"):
        stale.unlink()

    scene_bounds_min, scene_bounds_max = bounds_for(splats, range(len(splats)))
    payload_writer = PayloadWriter(payload_dir, payload_file_max_mb, payload_profile)
    nodes_json: list[dict[str, Any]] = []
    chunks_json: list[dict[str, Any]] = []
    leaf_original_splats = 0
    internal_summary_splats = 0

    for runtime_node in nodes:
        if lod_mode == "parent-summary":
            layers, chunks, lod_metadata = write_parent_summary_layers_for_node(
                runtime_node=runtime_node,
                splats=splats,
                payload_writer=payload_writer,
                summary_target_ratio=summary_target_ratio,
                summary_max_splats=summary_max_splats,
            )
            if runtime_node.children:
                internal_summary_splats += sum(chunk["splatCount"] for chunk in chunks)
            else:
                leaf_original_splats += sum(chunk["splatCount"] for chunk in chunks)
        else:
            layers, chunks = write_layers_for_node(
                runtime_node,
                splats,
                payload_writer,
                base_ratio,
                min_refinement_splats,
            )
            lod_metadata = {
                "estimatedError": round(1.0 / (runtime_node.depth + 2), 6),
                "refinementPolicy": "base-by-importance-then-refinement",
                "lodMode": "duplicated-parent",
                "lodRole": "duplicated-original",
            }
            if runtime_node.children:
                internal_summary_splats += 0
            else:
                leaf_original_splats += sum(chunk["splatCount"] for chunk in chunks)
        nodes_json.append({
            "id": runtime_node.id,
            "parent": runtime_node.parent,
            "children": runtime_node.children,
            "bounds": aabb(runtime_node.bounds_min, runtime_node.bounds_max),
            "layers": layers,
            "lod": lod_metadata,
            "runtimeHints": {
                "priority": max(10, 100 - runtime_node.depth * 15),
                "decodeCost": round(1.0 + runtime_node.depth * 0.35, 3),
                "gpuUploadBytes": sum(c["runtimeHints"]["gpuUploadBytes"] for c in chunks),
                "cachePolicy": "keep-near-camera" if runtime_node.depth <= 1 else "evict-when-far",
            },
        })
        chunks_json.extend(chunks)

    payload_writer.close()
    total_payload_splats = sum(chunk["splatCount"] for chunk in chunks_json)
    payload_bytes = sum(chunk["byteLength"] for chunk in chunks_json)
    first_render_bytes = sum(chunk["byteLength"] for chunk in chunks_json if chunk["layer"] in {"root.base"})
    converted_splats = len(splats)
    if lod_mode == "parent-summary":
        original_duplicate_ratio = round(leaf_original_splats / converted_splats, 6)
        duplicate_ratio = original_duplicate_ratio
        summary_overhead = round(internal_summary_splats / converted_splats, 6)
    else:
        original_duplicate_ratio = round(total_payload_splats / converted_splats, 6)
        duplicate_ratio = original_duplicate_ratio
        summary_overhead = 0.0
    total_storage_overhead = round(total_payload_splats / converted_splats, 6)
    statistics = {
        "sourceVertexCount": header.vertex_count,
        "convertedSplats": converted_splats,
        "leafOriginalSplats": leaf_original_splats,
        "internalSummarySplats": internal_summary_splats,
        "totalPayloadSplats": total_payload_splats,
        "duplicateRatio": duplicate_ratio,
        "originalDuplicateRatio": original_duplicate_ratio,
        "summaryOverhead": summary_overhead,
        "totalStorageOverhead": total_storage_overhead,
        "firstRenderBytes": first_render_bytes,
        "payloadBytes": payload_bytes,
        "nodeCount": len(nodes_json),
        "chunkCount": len(chunks_json),
    }

    sh_metadata = input_sh_metadata(header, payload_profile)
    scene_doc = {
        "format": "W3GS",
        "version": "0.1",
        "asset": {
            "generator": "ply-to-w3gs converter",
            "source": str(input_path),
            "sourceVertexCount": header.vertex_count,
            "convertedSplats": len(splats),
            "sampling": "evenly-strided by vertex index" if len(splats) < header.vertex_count else "full",
            "payloadStatus": "generated-raw",
            "lodMode": lod_mode,
            "payloadProfile": payload_profile.id,
        },
        "scene": {
            "name": output_dir.name,
            "description": "W3GS Prototype 1 sample converted from a 3DGS PLY.",
            "coordinateSystem": "local",
            "upAxis": "Y",
            "units": "meter",
        },
        "bounds": aabb(scene_bounds_min, scene_bounds_max),
        "files": {
            "nodes": "nodes.w3gs.json",
            "chunks": "chunks.w3gs.json",
            "payloadBaseUri": "payload/",
        },
        "codecs": [{
            "id": payload_profile.id,
            "kind": "raw",
            "attributeSchema": payload_profile.schema_id,
            "decodeTarget": "cpu",
            "description": payload_profile.description,
        }],
        "entry": {
            "rootNode": "root",
            "startupSet": ["root.base"],
            "startupPolicy": "show-root-base-before-refinement",
        },
        "runtimeProfiles": {
            "desktop": {
                "memoryBudgetMB": 512,
                "maxConcurrentRequests": 8,
                "preferredCodec": payload_profile.id,
            }
        },
        "converter": {
            "lodMode": lod_mode,
            "baseRatio": base_ratio,
            "minRefinementSplats": min_refinement_splats,
            "summaryMethod": "grid-cluster-merge-v0" if lod_mode == "parent-summary" else None,
            "summaryShMethod": "importance-weighted-coefficient-average-v0" if lod_mode == "parent-summary" and payload_profile.sh_degree == 3 else None,
            "summaryTargetRatio": summary_target_ratio,
            "summaryMaxSplats": summary_max_splats,
            "payloadProfile": payload_profile.id,
            "bytesPerSplat": payload_profile.record_struct.size,
            **sh_metadata,
            "inputFormat": header.format,
            "inputProperties": header.property_names,
            "fRestCount": header.f_rest_count,
            "selectedInputVertexRange": [selected_indices[0], selected_indices[-1]] if selected_indices else None,
            "statistics": statistics,
        },
    }

    nodes_doc = {
        "version": "0.1",
        "tree": {
            "root": "root",
            "nodeCount": len(nodes_json),
            "relationship": "explicit-parent-and-children",
            "builder": "simple-octree",
        },
        "nodes": nodes_json,
    }
    chunks_doc = {
        "version": "0.1",
        "payloadStatus": "generated-raw",
        "attributeSchemas": {payload_profile.schema_id: attribute_schema_for(payload_profile)},
        "chunks": chunks_json,
    }

    write_json(output_dir / "scene.w3gs.json", scene_doc)
    write_json(output_dir / "nodes.w3gs.json", nodes_doc)
    write_json(output_dir / "chunks.w3gs.json", chunks_doc)

    check_consistency(output_dir, nodes_doc, chunks_doc)
    print(json.dumps({"lodMode": lod_mode, "payloadProfile": payload_profile.id, "statistics": statistics}, ensure_ascii=False, indent=2))


def attribute_schema_for(profile: PayloadProfile) -> dict[str, Any]:
    byte_offset = 0
    attributes = []
    for name, scalar_type, components in profile.attributes:
        attributes.append({
            "name": name,
            "type": scalar_type,
            "components": components,
            "byteOffset": byte_offset,
        })
        byte_offset += components * 4
    schema: dict[str, Any] = {
        "attributes": attributes,
        "bytesPerSplat": profile.record_struct.size,
        "endianness": "little",
        "packing": "packed-float32-no-padding",
        "quaternionOrder": "wxyz",
        "shDegree": profile.sh_degree,
    }
    if profile.sh_degree == 3:
        schema.update({
            "shCoefficientLayout": "graphdeco-channel-major-v1",
            "shRestOrder": "R.c1..c15,G.c1..c15,B.c1..c15",
            "shDirection": "position-minus-camera",
            "shColorActivation": "max(0,0.5+evalSH)",
        })
    else:
        schema["colorEncoding"] = "linear-rgb-from-sh0-clamped"
    return schema


def write_parent_summary_layers_for_node(
    runtime_node: RuntimeNode,
    splats: list[Splat],
    payload_writer: "PayloadWriter",
    summary_target_ratio: float,
    summary_max_splats: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    layer_id = f"{runtime_node.id}.base"
    chunk_id = f"chunk.{layer_id}"
    source_count = len(runtime_node.indices)

    if runtime_node.children:
        summary = summarize_node_splats(
            runtime_node=runtime_node,
            splats=splats,
            target_ratio=summary_target_ratio,
            max_summary_splats=summary_max_splats,
        )
        payload_splats = summary.splats
        lod_role = "summary"
        summary_method = "grid-cluster-merge-v0"
        summary_count = summary.summary_splat_count
        approx_error = summary.approx_error
        geometric_error = summary.geometric_error
        grid_size = summary.grid_size
    else:
        original_indices = sorted(runtime_node.indices, key=lambda idx: splats[idx].importance, reverse=True)
        payload_splats = [splats[idx] for idx in original_indices]
        lod_role = "leaf"
        summary_method = None
        summary_count = len(payload_splats)
        approx_error = 0.0
        geometric_error = bbox_diagonal(runtime_node.bounds_min, runtime_node.bounds_max)
        grid_size = (0, 0, 0)

    payload_ref = payload_writer.write_chunk(chunk_id, payload_splats)
    storage_overhead = round(summary_count / source_count, 6) if source_count else 0.0
    summary_sh_method = (
        "importance-weighted-coefficient-average-v0"
        if payload_writer.profile.sh_degree == 3 and lod_role == "summary"
        else None
    )
    layer_doc = {
        "id": layer_id,
        "level": 0,
        "kind": "base",
        "chunk": chunk_id,
        "splatCount": summary_count,
        "refinementMode": "replacement",
        "lodRole": lod_role,
        "sourceSplatCount": source_count,
        "summarySplatCount": summary_count if lod_role == "summary" else None,
        "summaryMethod": summary_method,
        "summaryShMethod": summary_sh_method,
        "approxError": round(approx_error, 6),
        "geometricError": round(geometric_error, 6),
        "storageOverhead": storage_overhead,
    }
    chunk_doc = {
        "id": chunk_id,
        "uri": payload_ref["uri"],
        "byteOffset": payload_ref["byteOffset"],
        "byteLength": payload_ref["byteLength"],
        "codec": payload_writer.profile.id,
        "attributeSchema": payload_writer.profile.schema_id,
        "node": runtime_node.id,
        "layer": layer_id,
        "level": 0,
        "splatCount": summary_count,
        "dependencies": [],
        "bounds": aabb(runtime_node.bounds_min, runtime_node.bounds_max),
        "lodRole": lod_role,
        "refinementMode": "replacement",
        "summaryMethod": summary_method,
        "summaryShMethod": summary_sh_method,
        "sourceSplatCount": source_count,
        "summarySplatCount": summary_count if lod_role == "summary" else None,
        "approxError": round(approx_error, 6),
        "geometricError": round(geometric_error, 6),
        "storageOverhead": storage_overhead,
        "gpuLayout": {"preferredOrder": "importance", "alignment": 16, "interleaved": True},
        "runtimeHints": {
            "priority": max(1, 100 - runtime_node.depth * 15),
            "decodeCost": round(1.0 + summary_count / 100_000, 3),
            "gpuUploadBytes": payload_ref["byteLength"],
        },
    }
    lod_metadata = {
        "estimatedError": round(approx_error, 6),
        "approxError": round(approx_error, 6),
        "geometricError": round(geometric_error, 6),
        "refinementPolicy": "hierarchical-replacement",
        "refinementMode": "replacement",
        "lodMode": "parent-summary",
        "lodRole": lod_role,
        "summaryMethod": summary_method,
        "sourceSplatCount": source_count,
        "summarySplatCount": summary_count if lod_role == "summary" else None,
        "gridSize": list(grid_size),
        "targetRatio": summary_target_ratio if lod_role == "summary" else None,
        "storageOverhead": storage_overhead,
        "opacityWeight": "opacity",
        "scaleWeight": "max-scale-squared",
        "colorWeight": "importance-weighted-dc",
        "shOrder": payload_writer.profile.sh_degree,
        "summaryShMethod": summary_sh_method,
    }
    return [layer_doc], [chunk_doc], lod_metadata


def summarize_node_splats(
    runtime_node: RuntimeNode,
    splats: list[Splat],
    target_ratio: float,
    max_summary_splats: int,
) -> SummaryResult:
    source_count = len(runtime_node.indices)
    effective_max_summary_splats = max(1, max_summary_splats)
    target_count = max(1, math.ceil(source_count * max(0.0001, target_ratio)))
    target_count = min(source_count, effective_max_summary_splats, target_count)
    grid_dim = max(1, math.ceil(target_count ** (1.0 / 3.0)))
    extent = tuple(max(1e-9, runtime_node.bounds_max[i] - runtime_node.bounds_min[i]) for i in range(3))

    buckets: dict[tuple[int, int, int], list[int]] = {}
    for idx in runtime_node.indices:
        s = splats[idx]
        key = (
            grid_coord(s.x, runtime_node.bounds_min[0], extent[0], grid_dim),
            grid_coord(s.y, runtime_node.bounds_min[1], extent[1], grid_dim),
            grid_coord(s.z, runtime_node.bounds_min[2], extent[2], grid_dim),
        )
        buckets.setdefault(key, []).append(idx)

    summary_splats: list[Splat] = []
    approx_error_sum = 0.0
    geometric_error = 0.0
    for indices in buckets.values():
        merged, cluster_approx_error, cluster_geometric_error = merge_splat_cluster(splats, indices)
        summary_splats.append(merged)
        approx_error_sum += cluster_approx_error * len(indices)
        geometric_error = max(geometric_error, cluster_geometric_error)

    summary_splats.sort(key=lambda splat: splat.importance, reverse=True)
    if len(summary_splats) > effective_max_summary_splats:
        summary_splats = summary_splats[:effective_max_summary_splats]
    approx_error = approx_error_sum / source_count if source_count else 0.0
    return SummaryResult(
        splats=summary_splats,
        source_splat_count=source_count,
        summary_splat_count=len(summary_splats),
        grid_size=(grid_dim, grid_dim, grid_dim),
        approx_error=approx_error,
        geometric_error=geometric_error,
    )


def grid_coord(value: float, min_value: float, extent: float, grid_dim: int) -> int:
    normalized = (value - min_value) / extent
    return max(0, min(grid_dim - 1, int(normalized * grid_dim)))


def merge_splat_cluster(splats: list[Splat], indices: list[int]) -> tuple[Splat, float, float]:
    weights: list[float] = []
    weight_sum = 0.0
    best_idx = indices[0]
    best_weight = -1.0
    min_pos = [math.inf, math.inf, math.inf]
    max_pos = [-math.inf, -math.inf, -math.inf]
    max_scale = [0.0, 0.0, 0.0]

    for idx in indices:
        s = splats[idx]
        footprint = max(s.scale) ** 2
        weight = max(1e-8, s.opacity * footprint)
        weights.append(weight)
        weight_sum += weight
        if weight > best_weight:
            best_weight = weight
            best_idx = idx
        for axis, value in enumerate((s.x, s.y, s.z)):
            min_pos[axis] = min(min_pos[axis], value)
            max_pos[axis] = max(max_pos[axis], value)
        for axis, value in enumerate(s.scale):
            max_scale[axis] = max(max_scale[axis], value)

    pos = [0.0, 0.0, 0.0]
    color = [0.0, 0.0, 0.0]
    sh_dc = [0.0, 0.0, 0.0]
    sh_rest = [0.0] * 45 if splats[indices[0]].sh_rest else []
    avg_scale = [0.0, 0.0, 0.0]
    log_transmittance = 0.0
    for idx, weight in zip(indices, weights):
        s = splats[idx]
        pos[0] += s.x * weight
        pos[1] += s.y * weight
        pos[2] += s.z * weight
        for axis in range(3):
            avg_scale[axis] += s.scale[axis] * weight
            color[axis] += s.color[axis] * weight
            sh_dc[axis] += s.sh_dc[axis] * weight
        for coefficient in range(len(sh_rest)):
            sh_rest[coefficient] += s.sh_rest[coefficient] * weight
        log_transmittance += math.log(max(1e-6, 1.0 - s.opacity))

    inv_weight = 1.0 / weight_sum
    pos = [value * inv_weight for value in pos]
    color = [clamp01(value * inv_weight) for value in color]
    sh_dc = [value * inv_weight for value in sh_dc]
    sh_rest = [value * inv_weight for value in sh_rest]
    avg_scale = [value * inv_weight for value in avg_scale]
    span = [max_pos[axis] - min_pos[axis] for axis in range(3)]
    scale = tuple(max(avg_scale[axis], max_scale[axis], span[axis] * 0.5 + max_scale[axis]) for axis in range(3))
    opacity = min(0.98, max(0.01, 1.0 - math.exp(log_transmittance)))
    rotation = splats[best_idx].rotation

    pos_variance = 0.0
    color_variance = 0.0
    for idx, weight in zip(indices, weights):
        s = splats[idx]
        pos_variance += weight * ((s.x - pos[0]) ** 2 + (s.y - pos[1]) ** 2 + (s.z - pos[2]) ** 2)
        color_variance += weight * sum((s.color[axis] - color[axis]) ** 2 for axis in range(3))
    pos_rms = math.sqrt(pos_variance * inv_weight)
    color_rms = math.sqrt(color_variance * inv_weight)
    cluster_diag = math.sqrt(sum(value * value for value in span))
    approx_error = pos_rms + color_rms * max(cluster_diag, 1e-6)
    geometric_error = max(pos_rms, cluster_diag * 0.5)

    importance = opacity * max(scale)
    return (
        Splat(pos[0], pos[1], pos[2], scale, rotation, opacity, tuple(color), tuple(sh_dc), tuple(sh_rest), importance),
        approx_error,
        geometric_error,
    )


def bbox_diagonal(bounds_min: tuple[float, float, float], bounds_max: tuple[float, float, float]) -> float:
    return math.sqrt(sum((bounds_max[i] - bounds_min[i]) ** 2 for i in range(3)))


def write_layers_for_node(
    runtime_node: RuntimeNode,
    splats: list[Splat],
    payload_writer: "PayloadWriter",
    base_ratio: float,
    min_refinement_splats: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sorted_indices = sorted(runtime_node.indices, key=lambda idx: splats[idx].importance, reverse=True)
    has_refinement = len(sorted_indices) >= min_refinement_splats
    base_count = len(sorted_indices)
    if has_refinement:
        base_count = max(1, min(len(sorted_indices), math.ceil(len(sorted_indices) * base_ratio)))

    layer_specs = [("base", 0, sorted_indices[:base_count], "replace-by-children" if runtime_node.children else "additive")]
    if has_refinement and base_count < len(sorted_indices):
        layer_specs.append(("r1", 1, sorted_indices[base_count:], "additive"))

    layers: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    previous_chunk_ids: list[str] = []
    for suffix, level, indices, refinement_mode in layer_specs:
        layer_id = f"{runtime_node.id}.{suffix}"
        chunk_id = f"chunk.{layer_id}"
        payload_ref = payload_writer.write_chunk(chunk_id, (splats[i] for i in indices))
        layer_doc = {
            "id": layer_id,
            "level": level,
            "kind": "base" if level == 0 else "refinement",
            "chunk": chunk_id,
            "splatCount": len(indices),
            "refinementMode": refinement_mode,
            "lodRole": "duplicated-original",
            "sourceSplatCount": len(indices),
        }
        chunk_doc = {
            "id": chunk_id,
            "uri": payload_ref["uri"],
            "byteOffset": payload_ref["byteOffset"],
            "byteLength": payload_ref["byteLength"],
            "codec": payload_writer.profile.id,
            "attributeSchema": payload_writer.profile.schema_id,
            "node": runtime_node.id,
            "layer": layer_id,
            "level": level,
            "splatCount": len(indices),
            "dependencies": previous_chunk_ids[:],
            "bounds": aabb(runtime_node.bounds_min, runtime_node.bounds_max),
            "lodRole": "duplicated-original",
            "refinementMode": refinement_mode,
            "sourceSplatCount": len(indices),
            "gpuLayout": {"preferredOrder": "importance", "alignment": 16, "interleaved": True},
            "runtimeHints": {
                "priority": max(1, 100 - runtime_node.depth * 15 - level * 25),
                "decodeCost": round(1.0 + level * 0.8 + len(indices) / 100_000, 3),
                "gpuUploadBytes": payload_ref["byteLength"],
            },
        }
        layers.append(layer_doc)
        chunks.append(chunk_doc)
        previous_chunk_ids.append(chunk_id)
    return layers, chunks


class PayloadWriter:
    def __init__(self, payload_dir: Path, max_file_mb: float, profile: PayloadProfile) -> None:
        self.payload_dir = payload_dir
        self.profile = profile
        self.max_file_bytes = max(1, int(max_file_mb * MB))
        self.file_index = -1
        self.current: Any = None
        self.current_size = 0
        self.open_next()

    def open_next(self) -> None:
        if self.current:
            self.current.close()
        self.file_index += 1
        self.current_size = 0
        self.current = (self.payload_dir / f"chunks-{self.file_index}.bin").open("wb")

    def write_chunk(self, chunk_id: str, splats: Iterable[Splat]) -> dict[str, Any]:
        encoded = bytearray()
        count = 0
        for splat in splats:
            common = (splat.x, splat.y, splat.z, *splat.scale, *splat.rotation, splat.opacity)
            if self.profile.sh_degree == 3:
                encoded += self.profile.record_struct.pack(*common, *splat.sh_dc, *splat.sh_rest)
            else:
                encoded += self.profile.record_struct.pack(*common, *splat.color)
            count += 1
        if count == 0:
            raise ValueError(f"Chunk {chunk_id} has no splats.")
        if self.current_size and self.current_size + len(encoded) > self.max_file_bytes:
            self.open_next()
        offset = self.current_size
        self.current.write(encoded)
        self.current_size += len(encoded)
        return {
            "uri": f"chunks-{self.file_index}.bin",
            "byteOffset": offset,
            "byteLength": len(encoded),
        }

    def close(self) -> None:
        if self.current:
            self.current.close()
            self.current = None


def aabb(bounds_min: tuple[float, float, float], bounds_max: tuple[float, float, float]) -> dict[str, Any]:
    return {
        "type": "aabb",
        "min": [round(v, 6) for v in bounds_min],
        "max": [round(v, 6) for v in bounds_max],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_consistency(output_dir: Path, nodes_doc: dict[str, Any], chunks_doc: dict[str, Any]) -> None:
    chunk_by_id = {chunk["id"]: chunk for chunk in chunks_doc["chunks"]}
    missing = []
    for node_doc in nodes_doc["nodes"]:
        for layer_doc in node_doc["layers"]:
            if layer_doc["chunk"] not in chunk_by_id:
                missing.append(layer_doc["chunk"])
    if missing:
        raise ValueError(f"Layer references missing chunks: {missing}")

    for chunk_doc in chunks_doc["chunks"]:
        payload_path = output_dir / "payload" / chunk_doc["uri"]
        if not payload_path.exists():
            raise ValueError(f"Missing payload file: {payload_path}")
        file_size = payload_path.stat().st_size
        end = chunk_doc["byteOffset"] + chunk_doc["byteLength"]
        if end > file_size:
            raise ValueError(f"Chunk {chunk_doc['id']} exceeds payload file size.")
        schema = chunks_doc["attributeSchemas"][chunk_doc["attributeSchema"]]
        expected = chunk_doc["splatCount"] * schema["bytesPerSplat"]
        if expected != chunk_doc["byteLength"]:
            raise ValueError(f"Chunk {chunk_doc['id']} byteLength mismatch: {chunk_doc['byteLength']} != {expected}")


if __name__ == "__main__":
    main()
