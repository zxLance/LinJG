from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from validate_w3gs import validate_directory  # noqa: E402


def base_documents() -> tuple[dict, dict, dict]:
    scene = {
        "format": "W3GS",
        "version": "0.1",
        "asset": {"generator": "validator-test", "payloadStatus": "generated-raw"},
        "scene": {"name": "fixture", "coordinateSystem": "local", "upAxis": "Y", "units": "meter"},
        "bounds": {"type": "aabb", "min": [0, 0, 0], "max": [1, 1, 1]},
        "files": {
            "nodes": "nodes.w3gs.json",
            "chunks": "chunks.w3gs.json",
            "payloadBaseUri": "payload/",
        },
        "codecs": [
            {
                "id": "raw-gaussian-v0",
                "kind": "raw",
                "attributeSchema": "gaussian-basic-v0",
                "decodeTarget": "cpu",
            }
        ],
        "entry": {
            "rootNode": "root",
            "startupSet": ["root.base"],
            "startupPolicy": "show-root-base-before-refinement",
        },
        "runtimeProfiles": {
            "desktop": {
                "memoryBudgetMB": 64,
                "maxConcurrentRequests": 4,
                "preferredCodec": "raw-gaussian-v0",
            }
        },
    }
    nodes = {
        "version": "0.1",
        "tree": {"root": "root", "nodeCount": 2, "relationship": "explicit-parent-and-children"},
        "nodes": [
            {
                "id": "root",
                "parent": None,
                "children": ["leaf"],
                "bounds": {"type": "aabb", "min": [0, 0, 0], "max": [1, 1, 1]},
                "layers": [
                    {
                        "id": "root.base",
                        "level": 0,
                        "kind": "base",
                        "chunk": "chunk.root.base",
                        "splatCount": 1,
                        "refinementMode": "replace-by-children",
                    }
                ],
                "lod": {"refinementPolicy": "prefer-children-then-refinement"},
            },
            {
                "id": "leaf",
                "parent": "root",
                "children": [],
                "bounds": {"type": "aabb", "min": [0, 0, 0], "max": [0.5, 0.5, 0.5]},
                "layers": [
                    {
                        "id": "leaf.base",
                        "level": 0,
                        "kind": "base",
                        "chunk": "chunk.leaf.base",
                        "splatCount": 1,
                        "refinementMode": "additive",
                    }
                ],
                "lod": {"refinementPolicy": "prefer-refinement"},
            },
        ],
    }
    chunks = {
        "version": "0.1",
        "payloadStatus": "generated-raw",
        "attributeSchemas": {
            "gaussian-basic-v0": {
                "attributes": [
                    {"name": "position", "type": "float32", "components": 3},
                    {"name": "scale", "type": "float32", "components": 3},
                    {"name": "rotation", "type": "float32", "components": 4},
                    {"name": "opacity", "type": "float32", "components": 1},
                    {"name": "color", "type": "float32", "components": 3},
                ],
                "bytesPerSplat": 56,
            }
        },
        "chunks": [
            {
                "id": "chunk.root.base",
                "uri": "chunks-0.bin",
                "byteOffset": 0,
                "byteLength": 56,
                "codec": "raw-gaussian-v0",
                "attributeSchema": "gaussian-basic-v0",
                "node": "root",
                "layer": "root.base",
                "level": 0,
                "splatCount": 1,
                "dependencies": [],
                "refinementMode": "replace-by-children",
                "runtimeHints": {"priority": 100, "decodeCost": 1.0, "gpuUploadBytes": 56},
            },
            {
                "id": "chunk.leaf.base",
                "uri": "chunks-0.bin",
                "byteOffset": 56,
                "byteLength": 56,
                "codec": "raw-gaussian-v0",
                "attributeSchema": "gaussian-basic-v0",
                "node": "leaf",
                "layer": "leaf.base",
                "level": 0,
                "splatCount": 1,
                "dependencies": ["chunk.root.base"],
                "refinementMode": "additive",
                "runtimeHints": {"priority": 50, "decodeCost": 1.0, "gpuUploadBytes": 56},
            },
        ],
    }
    return scene, nodes, chunks


def write_fixture(directory: Path, scene: dict, nodes: dict, chunks: dict, payload_bytes: int = 112) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload_dir = directory / "payload"
    payload_dir.mkdir()
    (directory / "scene.w3gs.json").write_text(json.dumps(scene), encoding="utf-8")
    (directory / "nodes.w3gs.json").write_text(json.dumps(nodes), encoding="utf-8")
    (directory / "chunks.w3gs.json").write_text(json.dumps(chunks), encoding="utf-8")
    (payload_dir / "chunks-0.bin").write_bytes(bytes(payload_bytes))


def use_sh3_profile(scene: dict, chunks: dict) -> None:
    scene["codecs"] = [{
        "id": "raw-gaussian-sh3-v0",
        "kind": "raw",
        "attributeSchema": "gaussian-sh3-v0",
        "decodeTarget": "cpu",
    }]
    scene["runtimeProfiles"]["desktop"]["preferredCodec"] = "raw-gaussian-sh3-v0"
    chunks["attributeSchemas"] = {
        "gaussian-sh3-v0": {
            "attributes": [
                {"name": "position", "type": "float32", "components": 3, "byteOffset": 0},
                {"name": "scale", "type": "float32", "components": 3, "byteOffset": 12},
                {"name": "rotation", "type": "float32", "components": 4, "byteOffset": 24},
                {"name": "opacity", "type": "float32", "components": 1, "byteOffset": 40},
                {"name": "shDc", "type": "float32", "components": 3, "byteOffset": 44},
                {"name": "shRest", "type": "float32", "components": 45, "byteOffset": 56},
            ],
            "bytesPerSplat": 236,
            "endianness": "little",
            "packing": "packed-float32-no-padding",
            "quaternionOrder": "wxyz",
            "shDegree": 3,
            "shCoefficientLayout": "graphdeco-channel-major-v1",
            "shRestOrder": "R.c1..c15,G.c1..c15,B.c1..c15",
            "shDirection": "position-minus-camera",
            "shColorActivation": "max(0,0.5+evalSH)",
        }
    }
    for index, chunk in enumerate(chunks["chunks"]):
        chunk["codec"] = "raw-gaussian-sh3-v0"
        chunk["attributeSchema"] = "gaussian-sh3-v0"
        chunk["byteOffset"] = index * 236
        chunk["byteLength"] = 236
        chunk["runtimeHints"]["gpuUploadBytes"] = 236


def error_codes(report) -> set[str]:
    return {issue.code for issue in report.issues if issue.severity == "ERROR"}


def warning_codes(report) -> set[str]:
    return {issue.code for issue in report.issues if issue.severity == "WARNING"}


class ValidatorMutationTests(unittest.TestCase):
    def validate_mutation(self, mutate=None, payload_bytes: int = 112):
        scene, nodes, chunks = (copy.deepcopy(value) for value in base_documents())
        if mutate:
            mutate(scene, nodes, chunks)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "sample"
            write_fixture(directory, scene, nodes, chunks, payload_bytes)
            return validate_directory(directory)

    def test_valid_fixture_has_no_errors(self):
        report = self.validate_mutation()
        self.assertTrue(report.valid, [issue.code for issue in report.issues])
        self.assertIn("STARTUP_FALLBACK_UNPROVABLE", warning_codes(report))

    def test_missing_chunk(self):
        report = self.validate_mutation(lambda _s, _n, c: c["chunks"].pop())
        self.assertIn("LAYER_CHUNK_MISSING", error_codes(report))

    def test_range_out_of_bounds(self):
        def mutate(_scene, _nodes, chunks):
            chunks["chunks"][1]["byteOffset"] = 1000

        report = self.validate_mutation(mutate)
        self.assertIn("CHUNK_RANGE_OUT_OF_BOUNDS", error_codes(report))

    def test_parent_child_mismatch(self):
        def mutate(_scene, nodes, _chunks):
            nodes["nodes"][1]["parent"] = None

        report = self.validate_mutation(mutate)
        self.assertTrue({"CHILD_PARENT_MISMATCH", "NODE_PARENT_MISSING"} & error_codes(report))

    def test_dependency_cycle(self):
        def mutate(_scene, _nodes, chunks):
            chunks["chunks"][0]["dependencies"] = ["chunk.leaf.base"]

        report = self.validate_mutation(mutate)
        self.assertIn("DEPENDENCY_CYCLE", error_codes(report))

    def test_unknown_codec_is_warning_not_fake_success(self):
        def mutate(scene, _nodes, chunks):
            scene["codecs"].append(
                {
                    "id": "mystery-v0",
                    "kind": "mystery",
                    "attributeSchema": "gaussian-basic-v0",
                    "decodeTarget": "worker",
                }
            )
            chunks["chunks"][1]["codec"] = "mystery-v0"

        report = self.validate_mutation(mutate)
        self.assertTrue(report.valid)
        self.assertIn("CODEC_UNVERIFIED", warning_codes(report))

    def test_raw_stride_mismatch(self):
        def mutate(_scene, _nodes, chunks):
            chunks["chunks"][1]["byteLength"] = 55
            chunks["chunks"][1]["runtimeHints"]["gpuUploadBytes"] = 55

        report = self.validate_mutation(mutate)
        self.assertIn("RAW_GAUSSIAN_CHUNK_LENGTH", error_codes(report))
        self.assertIn("CHUNK_STRIDE_MISMATCH", error_codes(report))

    def test_bad_startup_set(self):
        def mutate(scene, _nodes, _chunks):
            scene["entry"]["startupSet"] = ["missing.layer"]

        report = self.validate_mutation(mutate)
        self.assertIn("STARTUP_LAYER_MISSING", error_codes(report))

    def test_missing_chunk_splat_count_cannot_bypass_stride_check(self):
        def mutate(_scene, _nodes, chunks):
            del chunks["chunks"][1]["splatCount"]

        report = self.validate_mutation(mutate)
        self.assertIn("CHUNK_REQUIRED_INTEGER", error_codes(report))

    def test_shared_range_with_conflicting_decode_metadata(self):
        def mutate(scene, nodes, chunks):
            scene["codecs"].append(
                {
                    "id": "alias-codec-v0",
                    "kind": "alias",
                    "attributeSchema": "gaussian-basic-v0",
                    "decodeTarget": "cpu",
                }
            )
            chunks["chunks"][1]["byteOffset"] = 0
            chunks["chunks"][1]["codec"] = "alias-codec-v0"
            chunks["chunks"][1]["sharedRange"] = True
            chunks["chunks"][0]["sharedRange"] = True

        report = self.validate_mutation(mutate)
        self.assertIn("CHUNK_SHARED_RANGE_CONFLICT", error_codes(report))

    def test_runtime_priority_scale_is_advisory(self):
        def mutate(_scene, _nodes, chunks):
            chunks["chunks"][1]["runtimeHints"]["priority"] = 1000

        report = self.validate_mutation(mutate)
        self.assertTrue(report.valid)
        self.assertIn("RUNTIME_PRIORITY_REFERENCE_RANGE", warning_codes(report))

    def test_gpu_upload_bytes_may_include_renderer_repacking(self):
        def mutate(_scene, _nodes, chunks):
            chunks["chunks"][1]["runtimeHints"]["gpuUploadBytes"] = 64

        report = self.validate_mutation(mutate)
        self.assertTrue(report.valid)
        self.assertIn("CHUNK_GPU_BYTES_DIFFER", warning_codes(report))

    def test_lod_role_cannot_be_used_as_layer_kind(self):
        def mutate(_scene, nodes, _chunks):
            nodes["nodes"][0]["layers"][0]["kind"] = "summary"
            nodes["nodes"][0]["layers"][0]["lodRole"] = "summary"

        report = self.validate_mutation(mutate)
        self.assertIn("LAYER_KIND", error_codes(report))

    def test_unsupported_version_cannot_report_conformance_pass(self):
        def mutate(scene, nodes, chunks):
            scene["version"] = "0.2"
            nodes["version"] = "0.2"
            chunks["version"] = "0.2"

        report = self.validate_mutation(mutate)
        self.assertIn("VERSION_UNSUPPORTED", error_codes(report))

    def test_valid_sh3_profile(self):
        def mutate(scene, _nodes, chunks):
            use_sh3_profile(scene, chunks)

        report = self.validate_mutation(mutate, payload_bytes=472)
        self.assertTrue(report.valid, [(issue.code, issue.message) for issue in report.issues])

    def test_sh3_stride_mismatch(self):
        def mutate(scene, _nodes, chunks):
            use_sh3_profile(scene, chunks)
            chunks["attributeSchemas"]["gaussian-sh3-v0"]["bytesPerSplat"] = 232

        report = self.validate_mutation(mutate, payload_bytes=472)
        self.assertIn("RAW_GAUSSIAN_SH3_STRIDE", error_codes(report))

    def test_sh3_missing_or_misordered_attributes(self):
        def mutate(scene, _nodes, chunks):
            use_sh3_profile(scene, chunks)
            attrs = chunks["attributeSchemas"]["gaussian-sh3-v0"]["attributes"]
            attrs[4], attrs[5] = attrs[5], attrs[4]

        report = self.validate_mutation(mutate, payload_bytes=472)
        self.assertIn("RAW_GAUSSIAN_SH3_LAYOUT", error_codes(report))

    def test_sh3_codec_schema_mismatch(self):
        def mutate(scene, _nodes, chunks):
            use_sh3_profile(scene, chunks)
            chunks["chunks"][1]["attributeSchema"] = "gaussian-basic-v0"
            chunks["attributeSchemas"]["gaussian-basic-v0"] = base_documents()[2]["attributeSchemas"]["gaussian-basic-v0"]

        report = self.validate_mutation(mutate, payload_bytes=472)
        self.assertIn("CHUNK_CODEC_SCHEMA_MISMATCH", error_codes(report))

    def test_sh3_semantic_metadata_mismatch(self):
        def mutate(scene, _nodes, chunks):
            use_sh3_profile(scene, chunks)
            chunks["attributeSchemas"]["gaussian-sh3-v0"]["shRestOrder"] = "coefficient-major"

        report = self.validate_mutation(mutate, payload_bytes=472)
        self.assertIn("RAW_GAUSSIAN_SH3_SEMANTICS", error_codes(report))


if __name__ == "__main__":
    unittest.main()
