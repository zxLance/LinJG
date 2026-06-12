#!/usr/bin/env python3
"""Independent cross-file conformance checker for W3GS data directories."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit


SUPPORTED_VERSIONS = {"0.1"}
KNOWN_REFINEMENT_MODES = {
    "additive",
    "replacement",
    "replace-by-children",
    "residual",
}
KNOWN_LAYER_KINDS = {"base", "refinement"}
KNOWN_LOD_ROLES = {"summary", "leaf", "duplicated-original"}
RAW_GAUSSIAN_V0_BYTES_PER_SPLAT = 56
RAW_GAUSSIAN_V0_LAYOUT = [
    ("position", "float32", 3),
    ("scale", "float32", 3),
    ("rotation", "float32", 4),
    ("opacity", "float32", 1),
    ("color", "float32", 3),
]
RAW_GAUSSIAN_SH3_V0_BYTES_PER_SPLAT = 236
RAW_GAUSSIAN_SH3_V0_LAYOUT = [
    ("position", "float32", 3),
    ("scale", "float32", 3),
    ("rotation", "float32", 4),
    ("opacity", "float32", 1),
    ("shDc", "float32", 3),
    ("shRest", "float32", 45),
]
RAW_GAUSSIAN_SH3_V0_OFFSETS = [0, 12, 24, 40, 44, 56]
KNOWN_RAW_CODECS = {"raw-gaussian-v0", "raw-gaussian-sh3-v0"}


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    location: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    directory: str
    issues: list[Issue] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)

    def add(
        self,
        severity: str,
        code: str,
        message: str,
        location: str = "",
        **details: Any,
    ) -> None:
        self.issues.append(Issue(severity, code, message, location, details))

    @property
    def error_count(self) -> int:
        return sum(issue.severity == "ERROR" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "WARNING" for issue in self.issues)

    @property
    def info_count(self) -> int:
        return sum(issue.severity == "INFO" for issue in self.issues)

    @property
    def valid(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": self.directory,
            "valid": self.valid,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
            },
            "statistics": self.statistics,
            "issues": [asdict(issue) for issue in self.issues],
        }


class W3GSValidator:
    def __init__(self, directory: Path) -> None:
        self.root = directory.resolve()
        self.report = ValidationReport(str(self.root))
        self.scene: dict[str, Any] = {}
        self.nodes_doc: dict[str, Any] = {}
        self.chunks_doc: dict[str, Any] = {}
        self.nodes: list[dict[str, Any]] = []
        self.chunks: list[dict[str, Any]] = []
        self.node_by_id: dict[str, dict[str, Any]] = {}
        self.chunk_by_id: dict[str, dict[str, Any]] = {}
        self.layer_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
        self.codec_by_id: dict[str, dict[str, Any]] = {}
        self.schemas: dict[str, dict[str, Any]] = {}
        self.payload_placeholder = False

    def validate(self) -> ValidationReport:
        if not self.root.exists() or not self.root.is_dir():
            self.report.add("ERROR", "DIRECTORY_NOT_FOUND", "W3GS directory does not exist.", str(self.root))
            return self.report

        scene_path = self.root / "scene.w3gs.json"
        self.scene = self._load_json(scene_path, "scene.w3gs.json")
        if not self.scene:
            return self.report

        self._validate_scene_top_level()
        nodes_path = self._resolve_manifest_file("nodes", "scene.files.nodes")
        chunks_path = self._resolve_manifest_file("chunks", "scene.files.chunks")
        if nodes_path is None or chunks_path is None:
            return self.report

        self.nodes_doc = self._load_json(nodes_path, "nodes.w3gs.json")
        self.chunks_doc = self._load_json(chunks_path, "chunks.w3gs.json")
        if not self.nodes_doc or not self.chunks_doc:
            return self.report

        self._validate_document_top_levels()
        self._collect_codecs_and_schemas()
        self._collect_nodes_layers_chunks()
        self._validate_tree()
        self._validate_cross_references()
        self._validate_chunk_files_and_ranges()
        self._validate_dependencies()
        self._validate_codecs_and_schemas()
        self._validate_startup_set()
        self._validate_refinement_semantics()
        self._validate_runtime_hints()
        self._finish_statistics()
        return self.report

    def _load_json(self, path: Path, location: str) -> dict[str, Any]:
        if not path.exists():
            self.report.add("ERROR", "JSON_FILE_MISSING", "Required JSON file does not exist.", location, path=str(path))
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.report.add("ERROR", "JSON_READ_ERROR", f"Cannot read valid UTF-8 JSON: {exc}", location)
            return {}
        if not isinstance(value, dict):
            self.report.add("ERROR", "JSON_TOP_LEVEL_TYPE", "Top-level JSON value must be an object.", location)
            return {}
        return value

    def _validate_scene_top_level(self) -> None:
        required = {
            "format": str,
            "version": str,
            "scene": dict,
            "bounds": dict,
            "files": dict,
            "codecs": list,
            "entry": dict,
        }
        self._require_fields(self.scene, required, "scene")
        if self.scene.get("format") != "W3GS":
            self.report.add("ERROR", "FORMAT_NAME", "scene.format must be 'W3GS'.", "scene.format")
        self._check_version(self.scene.get("version"), "scene.version")
        self._validate_aabb(self.scene.get("bounds"), "scene.bounds")

        asset = self.scene.get("asset", {})
        chunk_status = self.chunks_doc.get("payloadStatus") if self.chunks_doc else None
        statuses = [asset.get("payloadStatus") if isinstance(asset, dict) else None, chunk_status]
        self.payload_placeholder = any(value == "placeholder" for value in statuses)

    def _resolve_manifest_file(self, key: str, location: str) -> Path | None:
        files = self.scene.get("files")
        if not isinstance(files, dict):
            return None
        ref = files.get(key)
        if not isinstance(ref, str) or not ref:
            self.report.add("ERROR", "MANIFEST_FILE_REFERENCE", f"scene.files.{key} must be a non-empty relative path.", location)
            return None
        return self._safe_path(ref, location)

    def _validate_document_top_levels(self) -> None:
        self._require_fields(self.nodes_doc, {"version": str, "tree": dict, "nodes": list}, "nodes")
        self._require_fields(
            self.chunks_doc,
            {"version": str, "attributeSchemas": dict, "chunks": list},
            "chunks",
        )
        self._check_version(self.nodes_doc.get("version"), "nodes.version")
        self._check_version(self.chunks_doc.get("version"), "chunks.version")
        if self.chunks_doc.get("payloadStatus") == "placeholder":
            self.payload_placeholder = True
        scene_version = self.scene.get("version")
        for name, doc in (("nodes", self.nodes_doc), ("chunks", self.chunks_doc)):
            if isinstance(scene_version, str) and isinstance(doc.get("version"), str) and doc["version"] != scene_version:
                self.report.add(
                    "ERROR",
                    "VERSION_MISMATCH",
                    f"{name}.version does not match scene.version.",
                    f"{name}.version",
                    sceneVersion=scene_version,
                    documentVersion=doc["version"],
                )

    def _collect_codecs_and_schemas(self) -> None:
        codecs = self.scene.get("codecs") if isinstance(self.scene.get("codecs"), list) else []
        for index, codec in enumerate(codecs):
            location = f"scene.codecs[{index}]"
            if not isinstance(codec, dict):
                self.report.add("ERROR", "CODEC_TYPE", "Codec declaration must be an object.", location)
                continue
            codec_id = codec.get("id")
            if not isinstance(codec_id, str) or not codec_id:
                self.report.add("ERROR", "CODEC_ID", "Codec id must be a non-empty string.", f"{location}.id")
                continue
            if codec_id in self.codec_by_id:
                self.report.add("ERROR", "CODEC_ID_DUPLICATE", "Codec id must be unique.", f"{location}.id", id=codec_id)
                continue
            self.codec_by_id[codec_id] = codec
            if not isinstance(codec.get("kind"), str) or not codec.get("kind"):
                self.report.add("ERROR", "CODEC_KIND", "Codec kind must be a non-empty string.", f"{location}.kind")
            if not isinstance(codec.get("attributeSchema"), str) or not codec.get("attributeSchema"):
                self.report.add("ERROR", "CODEC_SCHEMA_REFERENCE", "Codec must reference an attributeSchema.", f"{location}.attributeSchema")

        schemas = self.chunks_doc.get("attributeSchemas")
        if isinstance(schemas, dict):
            for schema_id, schema in schemas.items():
                if not isinstance(schema_id, str) or not schema_id or not isinstance(schema, dict):
                    self.report.add("ERROR", "ATTRIBUTE_SCHEMA_DECLARATION", "Attribute schema entries must be named objects.", "chunks.attributeSchemas")
                    continue
                self.schemas[schema_id] = schema

    def _collect_nodes_layers_chunks(self) -> None:
        raw_nodes = self.nodes_doc.get("nodes")
        self.nodes = raw_nodes if isinstance(raw_nodes, list) else []
        for index, node in enumerate(self.nodes):
            location = f"nodes.nodes[{index}]"
            if not isinstance(node, dict):
                self.report.add("ERROR", "NODE_TYPE", "Node must be an object.", location)
                continue
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                self.report.add("ERROR", "NODE_ID", "Node id must be a non-empty string.", f"{location}.id")
                continue
            if node_id in self.node_by_id:
                self.report.add("ERROR", "NODE_ID_DUPLICATE", "Node id must be unique.", f"{location}.id", id=node_id)
                continue
            self.node_by_id[node_id] = node
            self._validate_aabb(node.get("bounds"), f"node[{node_id}].bounds")
            layers = node.get("layers")
            if not isinstance(layers, list) or not layers:
                self.report.add("ERROR", "NODE_LAYERS", "Node must contain a non-empty layers array.", f"node[{node_id}].layers")
                continue
            seen_levels: set[int] = set()
            for layer_index, layer in enumerate(layers):
                layer_location = f"node[{node_id}].layers[{layer_index}]"
                if not isinstance(layer, dict):
                    self.report.add("ERROR", "LAYER_TYPE", "Layer must be an object.", layer_location)
                    continue
                layer_id = layer.get("id")
                if not isinstance(layer_id, str) or not layer_id:
                    self.report.add("ERROR", "LAYER_ID", "Layer id must be a non-empty string.", f"{layer_location}.id")
                    continue
                if layer_id in self.layer_by_id:
                    self.report.add("ERROR", "LAYER_ID_DUPLICATE", "Layer id must be globally unique.", f"{layer_location}.id", id=layer_id)
                else:
                    self.layer_by_id[layer_id] = (node_id, layer)
                level = layer.get("level")
                if not self._is_nonnegative_int(level):
                    self.report.add("ERROR", "LAYER_LEVEL", "Layer level must be a non-negative integer.", f"{layer_location}.level")
                elif level in seen_levels:
                    self.report.add("WARNING", "LAYER_LEVEL_DUPLICATE", "Node has multiple layers at the same level.", f"{layer_location}.level", level=level)
                else:
                    seen_levels.add(level)
                if not self._is_nonnegative_int(layer.get("splatCount")):
                    self.report.add("ERROR", "LAYER_SPLAT_COUNT", "Layer splatCount must be a non-negative integer.", f"{layer_location}.splatCount")

        raw_chunks = self.chunks_doc.get("chunks")
        self.chunks = raw_chunks if isinstance(raw_chunks, list) else []
        for index, chunk in enumerate(self.chunks):
            location = f"chunks.chunks[{index}]"
            if not isinstance(chunk, dict):
                self.report.add("ERROR", "CHUNK_TYPE", "Chunk must be an object.", location)
                continue
            chunk_id = chunk.get("id")
            if not isinstance(chunk_id, str) or not chunk_id:
                self.report.add("ERROR", "CHUNK_ID", "Chunk id must be a non-empty string.", f"{location}.id")
                continue
            if chunk_id in self.chunk_by_id:
                self.report.add("ERROR", "CHUNK_ID_DUPLICATE", "Chunk id must be unique.", f"{location}.id", id=chunk_id)
                continue
            self.chunk_by_id[chunk_id] = chunk
            for field_name in ("level", "splatCount"):
                if not self._is_nonnegative_int(chunk.get(field_name)):
                    self.report.add(
                        "ERROR",
                        "CHUNK_REQUIRED_INTEGER",
                        f"Chunk {field_name} must be a non-negative integer.",
                        f"chunk[{chunk_id}].{field_name}",
                    )

    def _validate_tree(self) -> None:
        entry = self.scene.get("entry") if isinstance(self.scene.get("entry"), dict) else {}
        tree = self.nodes_doc.get("tree") if isinstance(self.nodes_doc.get("tree"), dict) else {}
        scene_root = entry.get("rootNode")
        tree_root = tree.get("root")
        if not isinstance(scene_root, str) or not scene_root:
            self.report.add("ERROR", "ROOT_REFERENCE", "scene.entry.rootNode must reference the root node.", "scene.entry.rootNode")
            return
        if isinstance(tree_root, str) and tree_root != scene_root:
            self.report.add("ERROR", "ROOT_MISMATCH", "scene.entry.rootNode and nodes.tree.root must match.", "nodes.tree.root", sceneRoot=scene_root, treeRoot=tree_root)
        if scene_root not in self.node_by_id:
            self.report.add("ERROR", "ROOT_MISSING", "Root node does not exist.", "scene.entry.rootNode", root=scene_root)
            return

        declared_count = tree.get("nodeCount")
        if self._is_nonnegative_int(declared_count) and declared_count != len(self.nodes):
            self.report.add("ERROR", "NODE_COUNT_MISMATCH", "nodes.tree.nodeCount does not match nodes array length.", "nodes.tree.nodeCount", declared=declared_count, actual=len(self.nodes))

        for node_id, node in self.node_by_id.items():
            parent = node.get("parent")
            children = node.get("children")
            if not isinstance(children, list) or any(not isinstance(child, str) for child in children):
                self.report.add("ERROR", "NODE_CHILDREN_TYPE", "Node children must be an array of node ids.", f"node[{node_id}].children")
                children = []
            if len(children) != len(set(children)):
                self.report.add("ERROR", "NODE_CHILD_DUPLICATE", "Node children must not contain duplicates.", f"node[{node_id}].children")
            if node_id in children:
                self.report.add("ERROR", "NODE_SELF_CHILD", "Node cannot list itself as a child.", f"node[{node_id}].children")
            if node_id == scene_root:
                if parent is not None:
                    self.report.add("ERROR", "ROOT_PARENT", "Root node parent must be null.", f"node[{node_id}].parent")
            else:
                if not isinstance(parent, str) or parent not in self.node_by_id:
                    self.report.add("ERROR", "NODE_PARENT_MISSING", "Non-root node must reference an existing parent.", f"node[{node_id}].parent")
                elif node_id not in self._children_of(parent):
                    self.report.add("ERROR", "PARENT_CHILD_MISMATCH", "Parent does not list this node as a child.", f"node[{node_id}].parent", parent=parent)
            if parent == node_id:
                self.report.add("ERROR", "NODE_SELF_PARENT", "Node cannot be its own parent.", f"node[{node_id}].parent")
            for child_id in children:
                child = self.node_by_id.get(child_id)
                if child is None:
                    self.report.add("ERROR", "CHILD_NODE_MISSING", "Child reference does not exist.", f"node[{node_id}].children", child=child_id)
                elif child.get("parent") != node_id:
                    self.report.add("ERROR", "CHILD_PARENT_MISMATCH", "Child parent reference does not point back to this node.", f"node[{node_id}].children", child=child_id, childParent=child.get("parent"))

        reachable: set[str] = set()

        def mark_reachable(node_id: str) -> None:
            if node_id in reachable:
                return
            reachable.add(node_id)
            for child_id in self._children_of(node_id):
                if child_id in self.node_by_id:
                    mark_reachable(child_id)

        mark_reachable(scene_root)
        color: dict[str, int] = {}
        cycle_paths: list[list[str]] = []

        def visit(node_id: str, stack: list[str]) -> None:
            state = color.get(node_id, 0)
            if state == 1:
                if node_id in stack:
                    cycle_paths.append(stack[stack.index(node_id):] + [node_id])
                return
            if state == 2:
                return
            color[node_id] = 1
            for child_id in self._children_of(node_id):
                if child_id in self.node_by_id:
                    visit(child_id, stack + [node_id])
            color[node_id] = 2

        for node_id in self.node_by_id:
            visit(node_id, [])
        for cycle in cycle_paths:
            self.report.add("ERROR", "NODE_TREE_CYCLE", "Spatial node tree contains a cycle.", "nodes.tree", cycle=cycle)
        unreachable = sorted(set(self.node_by_id) - reachable)
        for node_id in unreachable:
            self.report.add("ERROR", "NODE_ORPHAN", "Node is not reachable from the declared root.", f"node[{node_id}]")

    def _validate_cross_references(self) -> None:
        for layer_id, (node_id, layer) in self.layer_by_id.items():
            chunk_id = layer.get("chunk")
            if not isinstance(chunk_id, str) or chunk_id not in self.chunk_by_id:
                self.report.add("ERROR", "LAYER_CHUNK_MISSING", "Layer references a missing chunk.", f"layer[{layer_id}].chunk", chunk=chunk_id)
                continue
            chunk = self.chunk_by_id[chunk_id]
            if chunk.get("node") != node_id:
                self.report.add("ERROR", "CHUNK_NODE_BACKREF", "Chunk node back-reference does not match the owning node.", f"chunk[{chunk_id}].node", expected=node_id, actual=chunk.get("node"))
            if chunk.get("layer") != layer_id:
                self.report.add("ERROR", "CHUNK_LAYER_BACKREF", "Chunk layer back-reference does not match the layer.", f"chunk[{chunk_id}].layer", expected=layer_id, actual=chunk.get("layer"))
            for field_name in ("level", "splatCount"):
                if field_name in layer and field_name in chunk and layer[field_name] != chunk[field_name]:
                    self.report.add("ERROR", "LAYER_CHUNK_FIELD_MISMATCH", f"Layer and chunk {field_name} values differ.", f"chunk[{chunk_id}].{field_name}", layerValue=layer[field_name], chunkValue=chunk[field_name])

        for chunk_id, chunk in self.chunk_by_id.items():
            node_id = chunk.get("node")
            layer_id = chunk.get("layer")
            if not isinstance(node_id, str) or node_id not in self.node_by_id:
                self.report.add("ERROR", "CHUNK_NODE_MISSING", "Chunk references a missing node.", f"chunk[{chunk_id}].node", node=node_id)
            if not isinstance(layer_id, str) or layer_id not in self.layer_by_id:
                self.report.add("ERROR", "CHUNK_LAYER_MISSING", "Chunk references a missing layer.", f"chunk[{chunk_id}].layer", layer=layer_id)
            elif self.layer_by_id[layer_id][1].get("chunk") != chunk_id:
                self.report.add("ERROR", "LAYER_CHUNK_BACKREF", "Referenced layer does not point back to this chunk.", f"chunk[{chunk_id}].layer", layer=layer_id)

    def _validate_chunk_files_and_ranges(self) -> None:
        payload_base = self.scene.get("files", {}).get("payloadBaseUri", "") if isinstance(self.scene.get("files"), dict) else ""
        if not isinstance(payload_base, str):
            self.report.add("ERROR", "PAYLOAD_BASE_URI", "scene.files.payloadBaseUri must be a relative path string.", "scene.files.payloadBaseUri")
            payload_base = ""
        ranges_by_path: dict[Path, list[tuple[int, int, str, dict[str, Any]]]] = {}
        missing_placeholder_files: set[Path] = set()

        for chunk_id, chunk in self.chunk_by_id.items():
            location = f"chunk[{chunk_id}]"
            uri = chunk.get("uri")
            if not isinstance(uri, str) or not uri:
                self.report.add("ERROR", "CHUNK_URI", "Chunk uri must be a non-empty relative path.", f"{location}.uri")
                continue
            combined = f"{payload_base.rstrip('/')}/{uri}" if payload_base else uri
            payload_path = self._safe_path(combined, f"{location}.uri")
            if payload_path is None:
                continue
            offset = chunk.get("byteOffset")
            length = chunk.get("byteLength")
            if not self._is_nonnegative_int(offset):
                self.report.add("ERROR", "CHUNK_BYTE_OFFSET", "byteOffset must be a non-negative integer.", f"{location}.byteOffset")
                continue
            if not self._is_positive_int(length):
                self.report.add("ERROR", "CHUNK_BYTE_LENGTH", "byteLength must be a positive integer.", f"{location}.byteLength")
                continue
            end = offset + length
            ranges_by_path.setdefault(payload_path, []).append((offset, end, chunk_id, chunk))
            if not payload_path.exists():
                if self.payload_placeholder:
                    if payload_path not in missing_placeholder_files:
                        self.report.add("WARNING", "PLACEHOLDER_PAYLOAD_MISSING", "Payload is declared as placeholder; file and byte ranges cannot be physically verified.", str(payload_path))
                        missing_placeholder_files.add(payload_path)
                else:
                    self.report.add("ERROR", "PAYLOAD_FILE_MISSING", "Chunk payload file does not exist.", str(payload_path), chunk=chunk_id)
                continue
            if not payload_path.is_file():
                self.report.add("ERROR", "PAYLOAD_NOT_FILE", "Chunk payload path is not a file.", str(payload_path))
                continue
            file_size = payload_path.stat().st_size
            if end > file_size:
                self.report.add("ERROR", "CHUNK_RANGE_OUT_OF_BOUNDS", "Chunk byte range exceeds payload file size.", location, end=end, fileSize=file_size)

        for payload_path, ranges in ranges_by_path.items():
            ordered = sorted(ranges, key=lambda item: (item[0], item[1], item[2]))
            for index, first in enumerate(ordered):
                for second in ordered[index + 1:]:
                    if second[0] >= first[1]:
                        break
                    exact = first[0] == second[0] and first[1] == second[1]
                    if exact:
                        compatible = all(first[3].get(key) == second[3].get(key) for key in ("codec", "attributeSchema", "splatCount"))
                        explicit = self._range_sharing_declared(first[3]) and self._range_sharing_declared(second[3])
                        if not compatible:
                            self.report.add("ERROR", "CHUNK_SHARED_RANGE_CONFLICT", "Chunks share an exact byte range but declare incompatible decoding metadata.", str(payload_path), chunks=[first[2], second[2]])
                        elif explicit:
                            self.report.add("INFO", "CHUNK_SHARED_RANGE", "Chunks explicitly share the same payload byte range.", str(payload_path), chunks=[first[2], second[2]])
                        else:
                            self.report.add("WARNING", "CHUNK_SHARED_RANGE_UNDECLARED", "Chunks share an exact range without an explicit sharing declaration.", str(payload_path), chunks=[first[2], second[2]])
                    else:
                        self.report.add("ERROR", "CHUNK_RANGE_OVERLAP", "Chunk byte ranges partially overlap; this is a suspicious conflict.", str(payload_path), chunks=[first[2], second[2]], ranges=[[first[0], first[1]], [second[0], second[1]]])

    def _validate_dependencies(self) -> None:
        graph: dict[str, list[str]] = {}
        for chunk_id, chunk in self.chunk_by_id.items():
            dependencies = chunk.get("dependencies", [])
            if not isinstance(dependencies, list) or any(not isinstance(dep, str) for dep in dependencies):
                self.report.add("ERROR", "DEPENDENCY_TYPE", "Chunk dependencies must be an array of chunk ids.", f"chunk[{chunk_id}].dependencies")
                dependencies = []
            if len(dependencies) != len(set(dependencies)):
                self.report.add("WARNING", "DEPENDENCY_DUPLICATE", "Chunk dependency list contains duplicates.", f"chunk[{chunk_id}].dependencies")
            graph[chunk_id] = list(dict.fromkeys(dependencies))
            for dependency in dependencies:
                if dependency not in self.chunk_by_id:
                    self.report.add("ERROR", "DEPENDENCY_MISSING", "Chunk dependency does not exist.", f"chunk[{chunk_id}].dependencies", dependency=dependency)
                if dependency == chunk_id:
                    self.report.add("ERROR", "DEPENDENCY_SELF", "Chunk cannot depend on itself.", f"chunk[{chunk_id}].dependencies")

        color: dict[str, int] = {}
        reported: set[tuple[str, ...]] = set()

        def visit(chunk_id: str, stack: list[str]) -> None:
            state = color.get(chunk_id, 0)
            if state == 1:
                if chunk_id in stack:
                    cycle = tuple(stack[stack.index(chunk_id):] + [chunk_id])
                    if cycle not in reported:
                        reported.add(cycle)
                        self.report.add("ERROR", "DEPENDENCY_CYCLE", "Chunk dependency graph contains a cycle.", "chunks.dependencies", cycle=list(cycle))
                return
            if state == 2:
                return
            color[chunk_id] = 1
            for dependency in graph.get(chunk_id, []):
                if dependency in graph:
                    visit(dependency, stack + [chunk_id])
            color[chunk_id] = 2

        for chunk_id in graph:
            visit(chunk_id, [])

    def _validate_codecs_and_schemas(self) -> None:
        for codec_id, codec in self.codec_by_id.items():
            schema_id = codec.get("attributeSchema")
            if isinstance(schema_id, str) and schema_id not in self.schemas:
                self.report.add("ERROR", "CODEC_SCHEMA_MISSING", "Codec references an undeclared attribute schema.", f"codec[{codec_id}].attributeSchema", schema=schema_id)
            if codec_id not in KNOWN_RAW_CODECS:
                self.report.add("WARNING", "CODEC_UNVERIFIED", "Codec is declared but this validator has no codec-specific semantic verifier.", f"codec[{codec_id}]")

        for schema_id, schema in self.schemas.items():
            stride = schema.get("bytesPerSplat")
            if not (self._is_positive_int(stride) or stride == "variable"):
                self.report.add("ERROR", "SCHEMA_STRIDE", "attributeSchema.bytesPerSplat must be a positive integer or 'variable'.", f"schema[{schema_id}].bytesPerSplat")

        raw_codec = self.codec_by_id.get("raw-gaussian-v0")
        if raw_codec:
            raw_schema_id = raw_codec.get("attributeSchema")
            raw_schema = self.schemas.get(raw_schema_id) if isinstance(raw_schema_id, str) else None
            if raw_schema:
                if raw_schema.get("bytesPerSplat") != RAW_GAUSSIAN_V0_BYTES_PER_SPLAT:
                    self.report.add("ERROR", "RAW_GAUSSIAN_STRIDE", "raw-gaussian-v0 requires 56 bytes per splat.", f"schema[{raw_schema_id}].bytesPerSplat", expected=56, actual=raw_schema.get("bytesPerSplat"))
                actual_layout = []
                attributes = raw_schema.get("attributes")
                if isinstance(attributes, list):
                    for attribute in attributes:
                        if isinstance(attribute, dict):
                            actual_layout.append((attribute.get("name"), attribute.get("type"), attribute.get("components")))
                if actual_layout != RAW_GAUSSIAN_V0_LAYOUT:
                    self.report.add("ERROR", "RAW_GAUSSIAN_LAYOUT", "raw-gaussian-v0 attribute layout does not match the known 14-float profile.", f"schema[{raw_schema_id}].attributes", expected=RAW_GAUSSIAN_V0_LAYOUT, actual=actual_layout)

        sh3_codec = self.codec_by_id.get("raw-gaussian-sh3-v0")
        if sh3_codec:
            sh3_schema_id = sh3_codec.get("attributeSchema")
            sh3_schema = self.schemas.get(sh3_schema_id) if isinstance(sh3_schema_id, str) else None
            if sh3_schema:
                if sh3_schema.get("bytesPerSplat") != RAW_GAUSSIAN_SH3_V0_BYTES_PER_SPLAT:
                    self.report.add("ERROR", "RAW_GAUSSIAN_SH3_STRIDE", "raw-gaussian-sh3-v0 requires 236 bytes per splat.", f"schema[{sh3_schema_id}].bytesPerSplat", expected=236, actual=sh3_schema.get("bytesPerSplat"))
                attributes = sh3_schema.get("attributes")
                actual_layout = []
                actual_offsets = []
                if isinstance(attributes, list):
                    for attribute in attributes:
                        if isinstance(attribute, dict):
                            actual_layout.append((attribute.get("name"), attribute.get("type"), attribute.get("components")))
                            actual_offsets.append(attribute.get("byteOffset"))
                if actual_layout != RAW_GAUSSIAN_SH3_V0_LAYOUT:
                    self.report.add("ERROR", "RAW_GAUSSIAN_SH3_LAYOUT", "raw-gaussian-sh3-v0 attribute order must be position, scale, rotation, opacity, shDc, shRest with 59 float32 values.", f"schema[{sh3_schema_id}].attributes", expected=RAW_GAUSSIAN_SH3_V0_LAYOUT, actual=actual_layout)
                if actual_offsets != RAW_GAUSSIAN_SH3_V0_OFFSETS:
                    self.report.add("ERROR", "RAW_GAUSSIAN_SH3_OFFSETS", "raw-gaussian-sh3-v0 attributes must use the packed byte offsets defined by the profile.", f"schema[{sh3_schema_id}].attributes", expected=RAW_GAUSSIAN_SH3_V0_OFFSETS, actual=actual_offsets)
                semantic_fields = {
                    "endianness": "little",
                    "packing": "packed-float32-no-padding",
                    "quaternionOrder": "wxyz",
                    "shDegree": 3,
                    "shCoefficientLayout": "graphdeco-channel-major-v1",
                    "shRestOrder": "R.c1..c15,G.c1..c15,B.c1..c15",
                    "shDirection": "position-minus-camera",
                    "shColorActivation": "max(0,0.5+evalSH)",
                }
                for field_name, expected in semantic_fields.items():
                    if sh3_schema.get(field_name) != expected:
                        self.report.add("ERROR", "RAW_GAUSSIAN_SH3_SEMANTICS", "raw-gaussian-sh3-v0 schema semantic metadata does not match the profile.", f"schema[{sh3_schema_id}].{field_name}", expected=expected, actual=sh3_schema.get(field_name))

        for chunk_id, chunk in self.chunk_by_id.items():
            codec_id = chunk.get("codec")
            schema_id = chunk.get("attributeSchema")
            if not isinstance(codec_id, str) or codec_id not in self.codec_by_id:
                self.report.add("ERROR", "CHUNK_CODEC_MISSING", "Chunk references an undeclared codec.", f"chunk[{chunk_id}].codec", codec=codec_id)
            if not isinstance(schema_id, str) or schema_id not in self.schemas:
                self.report.add("ERROR", "CHUNK_SCHEMA_MISSING", "Chunk references an undeclared attribute schema.", f"chunk[{chunk_id}].attributeSchema", schema=schema_id)
                continue
            codec = self.codec_by_id.get(codec_id)
            if codec and codec.get("attributeSchema") != schema_id:
                self.report.add("ERROR", "CHUNK_CODEC_SCHEMA_MISMATCH", "Chunk schema does not match its codec declaration.", f"chunk[{chunk_id}].attributeSchema", codecSchema=codec.get("attributeSchema"), chunkSchema=schema_id)
            schema = self.schemas[schema_id]
            stride = schema.get("bytesPerSplat")
            splat_count = chunk.get("splatCount")
            byte_length = chunk.get("byteLength")
            if self._is_positive_int(stride) and self._is_nonnegative_int(splat_count) and self._is_nonnegative_int(byte_length):
                expected = stride * splat_count
                if byte_length != expected:
                    self.report.add("ERROR", "CHUNK_STRIDE_MISMATCH", "Chunk byteLength does not equal splatCount multiplied by schema stride.", f"chunk[{chunk_id}].byteLength", expected=expected, actual=byte_length)
            elif stride == "variable":
                self.report.add("WARNING", "VARIABLE_STRIDE_UNVERIFIED", "Variable-size codec payload length cannot be derived from splatCount.", f"chunk[{chunk_id}]")
            if codec_id == "raw-gaussian-v0" and self._is_nonnegative_int(splat_count) and self._is_nonnegative_int(byte_length):
                expected_raw = RAW_GAUSSIAN_V0_BYTES_PER_SPLAT * splat_count
                if byte_length != expected_raw:
                    self.report.add("ERROR", "RAW_GAUSSIAN_CHUNK_LENGTH", "raw-gaussian-v0 chunk length must be splatCount * 56.", f"chunk[{chunk_id}].byteLength", expected=expected_raw, actual=byte_length)
            if codec_id == "raw-gaussian-sh3-v0" and self._is_nonnegative_int(splat_count) and self._is_nonnegative_int(byte_length):
                expected_raw = RAW_GAUSSIAN_SH3_V0_BYTES_PER_SPLAT * splat_count
                if byte_length != expected_raw:
                    self.report.add("ERROR", "RAW_GAUSSIAN_SH3_CHUNK_LENGTH", "raw-gaussian-sh3-v0 chunk length must be splatCount * 236.", f"chunk[{chunk_id}].byteLength", expected=expected_raw, actual=byte_length)

    def _validate_startup_set(self) -> None:
        entry = self.scene.get("entry") if isinstance(self.scene.get("entry"), dict) else {}
        startup_set = entry.get("startupSet")
        if not isinstance(startup_set, list) or not startup_set or any(not isinstance(item, str) for item in startup_set):
            self.report.add("ERROR", "STARTUP_SET", "scene.entry.startupSet must be a non-empty array of layer ids.", "scene.entry.startupSet")
            return
        if len(startup_set) != len(set(startup_set)):
            self.report.add("WARNING", "STARTUP_SET_DUPLICATE", "startupSet contains duplicate layer ids.", "scene.entry.startupSet")
        startup_chunks: set[str] = set()
        startup_nodes: set[str] = set()
        for layer_id in startup_set:
            pair = self.layer_by_id.get(layer_id)
            if pair is None:
                self.report.add("ERROR", "STARTUP_LAYER_MISSING", "startupSet references a missing layer.", "scene.entry.startupSet", layer=layer_id)
                continue
            node_id, layer = pair
            startup_nodes.add(node_id)
            chunk_id = layer.get("chunk")
            if isinstance(chunk_id, str) and chunk_id in self.chunk_by_id:
                startup_chunks.add(chunk_id)

        for chunk_id in startup_chunks:
            dependencies = self.chunk_by_id[chunk_id].get("dependencies", [])
            if isinstance(dependencies, list):
                for dependency in dependencies:
                    if dependency not in startup_chunks:
                        self.report.add("ERROR", "STARTUP_DEPENDENCY_MISSING", "startupSet is not dependency-closed.", "scene.entry.startupSet", chunk=chunk_id, dependency=dependency)

        root_id = entry.get("rootNode")
        if isinstance(root_id, str) and root_id not in startup_nodes:
            self.report.add("WARNING", "STARTUP_ROOT_COVERAGE_UNPROVEN", "startupSet does not include a root-node layer; complete initial scene coverage cannot be established.", "scene.entry.startupSet")
        self.report.add(
            "WARNING",
            "STARTUP_FALLBACK_UNPROVABLE",
            "References and dependency closure can be checked, but current fields cannot strictly prove that startupSet is visually renderable and complete on every conforming decoder.",
            "scene.entry.startupSet",
        )

    def _validate_refinement_semantics(self) -> None:
        for layer_id, (node_id, layer) in self.layer_by_id.items():
            mode = layer.get("refinementMode")
            if mode not in KNOWN_REFINEMENT_MODES:
                self.report.add("ERROR", "REFINEMENT_MODE", "Layer refinementMode is outside the known value domain.", f"layer[{layer_id}].refinementMode", value=mode)
            if mode == "replace-by-children" and not self._children_of(node_id):
                self.report.add("ERROR", "REFINEMENT_CHILDREN_REQUIRED", "replace-by-children requires the node to have children.", f"layer[{layer_id}].refinementMode")
            kind = layer.get("kind")
            if kind not in KNOWN_LAYER_KINDS:
                self.report.add("ERROR", "LAYER_KIND", "Layer kind is outside the known value domain.", f"layer[{layer_id}].kind", value=kind)
            lod_role = layer.get("lodRole")
            if lod_role is not None and lod_role not in KNOWN_LOD_ROLES:
                self.report.add("WARNING", "LOD_ROLE_UNKNOWN", "Layer lodRole is not recognized by this validator.", f"layer[{layer_id}].lodRole", value=lod_role)
            chunk_id = layer.get("chunk")
            chunk = self.chunk_by_id.get(chunk_id) if isinstance(chunk_id, str) else None
            if chunk and "refinementMode" in chunk and chunk.get("refinementMode") != mode:
                self.report.add("ERROR", "REFINEMENT_MODE_MISMATCH", "Layer and chunk refinementMode values differ.", f"chunk[{chunk_id}].refinementMode", layerMode=mode, chunkMode=chunk.get("refinementMode"))

        for node_id, node in self.node_by_id.items():
            lod = node.get("lod")
            if not isinstance(lod, dict):
                continue
            mode = lod.get("refinementMode")
            if mode is not None and mode not in KNOWN_REFINEMENT_MODES:
                self.report.add("ERROR", "NODE_REFINEMENT_MODE", "Node lod.refinementMode is outside the known value domain.", f"node[{node_id}].lod.refinementMode", value=mode)
            policy = lod.get("refinementPolicy")
            if policy is not None and (not isinstance(policy, str) or not policy):
                self.report.add("ERROR", "REFINEMENT_POLICY", "Node refinementPolicy must be a non-empty string.", f"node[{node_id}].lod.refinementPolicy")
            lod_role = lod.get("lodRole")
            if lod_role is not None and lod_role not in KNOWN_LOD_ROLES:
                self.report.add("WARNING", "NODE_LOD_ROLE_UNKNOWN", "Node lodRole is not recognized by this validator.", f"node[{node_id}].lod.lodRole", value=lod_role)
            enter = lod.get("screenSizeEnter")
            exit_ = lod.get("screenSizeExit")
            if enter is not None and not self._is_number_in_range(enter, 0, 1):
                self.report.add("ERROR", "SCREEN_SIZE_ENTER", "screenSizeEnter must be a finite number in [0, 1].", f"node[{node_id}].lod.screenSizeEnter")
            if exit_ is not None and not self._is_number_in_range(exit_, 0, 1):
                self.report.add("ERROR", "SCREEN_SIZE_EXIT", "screenSizeExit must be a finite number in [0, 1].", f"node[{node_id}].lod.screenSizeExit")
            if self._is_number(enter) and self._is_number(exit_) and exit_ > enter:
                self.report.add("WARNING", "SCREEN_SIZE_HYSTERESIS", "screenSizeExit is greater than screenSizeEnter; traversal hysteresis may be inverted.", f"node[{node_id}].lod")
            for field_name in ("estimatedError", "approxError", "geometricError", "opacityError", "densityRatio", "storageOverhead"):
                value = lod.get(field_name)
                if value is not None and (not self._is_number(value) or value < 0):
                    self.report.add("ERROR", "LOD_NUMERIC_RANGE", f"{field_name} must be a finite non-negative number.", f"node[{node_id}].lod.{field_name}")

    def _validate_runtime_hints(self) -> None:
        for kind, objects in (("node", self.node_by_id), ("chunk", self.chunk_by_id)):
            for object_id, value in objects.items():
                hints = value.get("runtimeHints")
                if hints is None:
                    continue
                location = f"{kind}[{object_id}].runtimeHints"
                if not isinstance(hints, dict):
                    self.report.add("ERROR", "RUNTIME_HINTS_TYPE", "runtimeHints must be an object.", location)
                    continue
                priority = hints.get("priority")
                if priority is not None and not self._is_number(priority):
                    self.report.add("ERROR", "RUNTIME_PRIORITY", "runtimeHints.priority must be a finite number.", f"{location}.priority")
                elif self._is_number(priority) and not 0 <= priority <= 100:
                    self.report.add(
                        "WARNING",
                        "RUNTIME_PRIORITY_REFERENCE_RANGE",
                        "runtimeHints.priority is outside the current reference convention [0, 100]; W3GS 0.1 does not define a normative priority scale.",
                        f"{location}.priority",
                    )
                decode_cost = hints.get("decodeCost")
                if decode_cost is not None and (not self._is_number(decode_cost) or decode_cost < 0):
                    self.report.add("ERROR", "RUNTIME_DECODE_COST", "runtimeHints.decodeCost must be a finite non-negative number.", f"{location}.decodeCost")
                gpu_bytes = hints.get("gpuUploadBytes")
                if gpu_bytes is not None and not self._is_nonnegative_int(gpu_bytes):
                    self.report.add("ERROR", "RUNTIME_GPU_BYTES", "runtimeHints.gpuUploadBytes must be a non-negative integer.", f"{location}.gpuUploadBytes")
                if (
                    kind == "chunk"
                    and value.get("codec") in KNOWN_RAW_CODECS
                    and self._is_nonnegative_int(gpu_bytes)
                    and self._is_nonnegative_int(value.get("byteLength"))
                    and gpu_bytes != value["byteLength"]
                ):
                    self.report.add(
                        "WARNING",
                        "CHUNK_GPU_BYTES_DIFFER",
                        "Chunk gpuUploadBytes differs from raw payload byteLength. This can be valid when a renderer repacks or augments GPU data; the current contract does not declare a normative direct-upload layout.",
                        f"{location}.gpuUploadBytes",
                        byteLength=value["byteLength"],
                        gpuUploadBytes=gpu_bytes,
                    )
                cache_policy = hints.get("cachePolicy")
                if cache_policy is not None and (not isinstance(cache_policy, str) or not cache_policy):
                    self.report.add("ERROR", "RUNTIME_CACHE_POLICY", "runtimeHints.cachePolicy must be a non-empty string.", f"{location}.cachePolicy")

        profiles = self.scene.get("runtimeProfiles")
        if profiles is not None:
            if not isinstance(profiles, dict):
                self.report.add("ERROR", "RUNTIME_PROFILES_TYPE", "runtimeProfiles must be an object.", "scene.runtimeProfiles")
            else:
                for profile_id, profile in profiles.items():
                    location = f"scene.runtimeProfiles[{profile_id}]"
                    if not isinstance(profile, dict):
                        self.report.add("ERROR", "RUNTIME_PROFILE_TYPE", "Runtime profile must be an object.", location)
                        continue
                    memory = profile.get("memoryBudgetMB")
                    if memory is not None and (not self._is_number(memory) or memory <= 0):
                        self.report.add("ERROR", "RUNTIME_MEMORY_BUDGET", "memoryBudgetMB must be a positive number.", f"{location}.memoryBudgetMB")
                    requests = profile.get("maxConcurrentRequests")
                    if requests is not None and not self._is_positive_int(requests):
                        self.report.add("ERROR", "RUNTIME_REQUEST_LIMIT", "maxConcurrentRequests must be a positive integer.", f"{location}.maxConcurrentRequests")
                    preferred = profile.get("preferredCodec")
                    if preferred is not None and preferred not in self.codec_by_id:
                        self.report.add("ERROR", "RUNTIME_CODEC_MISSING", "Runtime profile preferredCodec is not declared.", f"{location}.preferredCodec", codec=preferred)

        self.report.add(
            "INFO",
            "RUNTIME_HINTS_STRUCTURAL_ONLY",
            "Runtime hint types, ranges, and selected internal relationships were checked; their prediction accuracy and performance value were not validated.",
            "runtimeHints",
        )

    def _finish_statistics(self) -> None:
        payload_files = {
            chunk.get("uri") for chunk in self.chunks if isinstance(chunk, dict) and isinstance(chunk.get("uri"), str)
        }
        self.report.statistics = {
            "version": self.scene.get("version"),
            "nodes": len(self.node_by_id),
            "layers": len(self.layer_by_id),
            "chunks": len(self.chunk_by_id),
            "codecs": len(self.codec_by_id),
            "attributeSchemas": len(self.schemas),
            "payloadFilesReferenced": len(payload_files),
            "payloadStatus": "placeholder" if self.payload_placeholder else "physical",
        }

    def _safe_path(self, reference: str, location: str) -> Path | None:
        parsed = urlsplit(reference)
        decoded = unquote(parsed.path).replace("\\", "/")
        posix_path = PurePosixPath(decoded)
        windows_path = PureWindowsPath(decoded)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            self.report.add("ERROR", "UNSAFE_URI", "Only local relative paths without URL components are supported by this validator.", location, reference=reference)
            return None
        if not decoded or posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive or ".." in posix_path.parts:
            self.report.add("ERROR", "UNSAFE_URI", "Path must be non-empty, relative, and must not traverse outside the W3GS directory.", location, reference=reference)
            return None
        candidate = (self.root / Path(*posix_path.parts)).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            self.report.add("ERROR", "UNSAFE_URI", "Resolved path escapes the W3GS directory.", location, reference=reference)
            return None
        return candidate

    def _validate_aabb(self, value: Any, location: str) -> None:
        if not isinstance(value, dict) or value.get("type") != "aabb":
            self.report.add("ERROR", "AABB_TYPE", "Bounds must be an aabb object.", location)
            return
        minimum = value.get("min")
        maximum = value.get("max")
        if not self._numeric_vector3(minimum) or not self._numeric_vector3(maximum):
            self.report.add("ERROR", "AABB_VECTOR", "AABB min and max must be finite numeric vec3 values.", location)
            return
        if any(minimum[index] > maximum[index] for index in range(3)):
            self.report.add("ERROR", "AABB_ORDER", "AABB min components must not exceed max components.", location)

    def _check_version(self, value: Any, location: str) -> None:
        if not isinstance(value, str) or not value:
            self.report.add("ERROR", "VERSION_REQUIRED", "Format version must be a non-empty string.", location)
        elif value not in SUPPORTED_VERSIONS:
            self.report.add("ERROR", "VERSION_UNSUPPORTED", "Version is not covered by this validator release, so conformance cannot be established.", location, version=value)

    def _require_fields(self, obj: dict[str, Any], required: dict[str, type], location: str) -> None:
        for field_name, expected_type in required.items():
            if field_name not in obj:
                self.report.add("ERROR", "REQUIRED_FIELD", "Required top-level field is missing.", f"{location}.{field_name}")
            elif not isinstance(obj[field_name], expected_type):
                self.report.add("ERROR", "FIELD_TYPE", f"Field must be {expected_type.__name__}.", f"{location}.{field_name}")

    def _children_of(self, node_id: str) -> list[str]:
        node = self.node_by_id.get(node_id, {})
        children = node.get("children", []) if isinstance(node, dict) else []
        return [child for child in children if isinstance(child, str)] if isinstance(children, list) else []

    @staticmethod
    def _range_sharing_declared(chunk: dict[str, Any]) -> bool:
        return chunk.get("sharedRange") is True or chunk.get("rangeSharing") in {"shared", "alias"}

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    @classmethod
    def _is_number_in_range(cls, value: Any, minimum: float, maximum: float) -> bool:
        return cls._is_number(value) and minimum <= value <= maximum

    @staticmethod
    def _is_nonnegative_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @staticmethod
    def _is_positive_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    @classmethod
    def _numeric_vector3(cls, value: Any) -> bool:
        return isinstance(value, list) and len(value) == 3 and all(cls._is_number(component) for component in value)


def validate_directory(directory: str | Path) -> ValidationReport:
    return W3GSValidator(Path(directory)).validate()


def format_human(report: ValidationReport) -> str:
    lines = [f"W3GS conformance: {report.directory}"]
    for issue in report.issues:
        location = f" {issue.location}" if issue.location else ""
        lines.append(f"[{issue.severity}] {issue.code}{location}: {issue.message}")
        if issue.details:
            lines.append(f"  details: {json.dumps(issue.details, ensure_ascii=False, sort_keys=True)}")
    status = "PASS" if report.valid else "FAIL"
    lines.append(
        f"{status}: {report.error_count} error(s), {report.warning_count} warning(s), "
        f"{report.info_count} info message(s)"
    )
    if report.statistics:
        lines.append(f"statistics: {json.dumps(report.statistics, ensure_ascii=False, sort_keys=True)}")
    return "\n".join(lines)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a W3GS data directory independently of its converter or viewer.")
    parser.add_argument("directory", help="Directory containing scene.w3gs.json.")
    parser.add_argument("--format", choices=["human", "json"], default="human", help="Console report format. Default: human.")
    parser.add_argument("--json-output", help="Also write the complete JSON report to this path.")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_directory(args.directory)
    rendered_json = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    print(rendered_json if args.format == "json" else format_human(report))
    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered_json + "\n", encoding="utf-8")
    return 0 if report.valid else 1


if __name__ == "__main__":
    sys.exit(main())
