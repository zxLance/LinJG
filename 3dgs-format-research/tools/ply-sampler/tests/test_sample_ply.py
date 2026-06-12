from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from sample_ply import (  # noqa: E402
    PlySamplerError,
    output_header,
    read_ply_header,
    sample_ply,
    select_nested_indices,
)


def write_vertex_only_ply(path: Path, record_count: int = 20) -> list[bytes]:
    header = (
        b"ply\n"
        b"format binary_little_endian 1.0\n"
        b"comment fixture keeps this comment\n"
        + f"element vertex {record_count}\n".encode("ascii")
        + b"property uchar tag\n"
        + b"property float value\n"
        + b"end_header\n"
    )
    records = [struct.pack("<Bf", index % 256, index * 1.25 - 3.0) for index in range(record_count)]
    path.write_bytes(header + b"".join(records))
    return records


class SelectionTests(unittest.TestCase):
    def test_deterministic_selection(self):
        first = select_nested_indices(1000, [10, 100], seed=42)
        second = select_nested_indices(1000, [10, 100], seed=42)
        self.assertEqual(first, second)
        self.assertNotEqual(first, select_nested_indices(1000, [10, 100], seed=43))

    def test_nested_subset(self):
        selected = select_nested_indices(1000, [10, 100, 250], seed=20260611)
        self.assertLess(set(selected[10]), set(selected[100]))
        self.assertLess(set(selected[100]), set(selected[250]))


class PlySamplingTests(unittest.TestCase):
    def test_attributes_comments_and_record_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.ply"
            source_records = write_vertex_only_ply(source)
            output_dir = root / "outputs"
            manifest = sample_ply(source, output_dir, counts=[3, 8], seed=7, block_records=4, command="test")

            source_header = read_ply_header(source)
            self.assertEqual(source_header.record_size, 5)
            self.assertEqual(manifest["verification"]["nestedSubsetChecks"][0]["strictIndexSubset"], True)
            self.assertEqual(manifest["verification"]["nestedSubsetChecks"][0]["rawRecordBytesMatch"], True)

            for output in manifest["outputs"]:
                output_path = output_dir / output["path"]
                output_header_info = read_ply_header(output_path)
                self.assertEqual(output_header_info.properties, source_header.properties)
                self.assertEqual(output_header_info.comments, source_header.comments)
                selected_indices = select_nested_indices(20, [3, 8], seed=7)[output["vertexCount"]]
                with output_path.open("rb") as generated:
                    generated.seek(output_header_info.header_bytes)
                    output_records = [generated.read(source_header.record_size) for _ in selected_indices]
                self.assertEqual(output_records, [source_records[index] for index in selected_indices])

            saved_manifest = json.loads((output_dir / "dataset-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_manifest["source"]["propertyCount"], 2)
            self.assertEqual(saved_manifest["sampling"]["algorithm"], "splitmix64-priority-bottom-k-v1")

    def test_output_header_only_changes_vertex_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.ply"
            write_vertex_only_ply(source)
            header = read_ply_header(source)
            generated = output_header(header, 5)
            expected = b"".join(header.header_lines).replace(b"element vertex 20\n", b"element vertex 5\n")
            self.assertEqual(generated, expected)

    def test_non_vertex_element_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "mesh.ply"
            source.write_bytes(
                b"ply\n"
                b"format binary_little_endian 1.0\n"
                b"element vertex 1\n"
                b"property float x\n"
                b"element face 0\n"
                b"property list uchar int vertex_indices\n"
                b"end_header\n"
                + struct.pack("<f", 1.0)
            )
            with self.assertRaisesRegex(PlySamplerError, "Non-vertex elements"):
                read_ply_header(source)

    def test_ascii_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "ascii.ply"
            source.write_text(
                "ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nend_header\n1.0\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(PlySamplerError, "binary_little_endian"):
                read_ply_header(source)


if __name__ == "__main__":
    unittest.main()
