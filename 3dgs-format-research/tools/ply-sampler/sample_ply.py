#!/usr/bin/env python3
"""Create deterministic nested subsets of fixed-record binary PLY vertex data."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import struct
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MASK64 = (1 << 64) - 1
GOLDEN64 = 0x9E3779B97F4A7C15
DEFAULT_SEED = 20_260_611
DEFAULT_COUNTS = (10_000, 250_000)
DEFAULT_BLOCK_RECORDS = 16_384

PLY_SCALAR_SIZES = {
    "char": 1,
    "uchar": 1,
    "int8": 1,
    "uint8": 1,
    "short": 2,
    "ushort": 2,
    "int16": 2,
    "uint16": 2,
    "int": 4,
    "uint": 4,
    "int32": 4,
    "uint32": 4,
    "float": 4,
    "float32": 4,
    "double": 8,
    "float64": 8,
}


class PlySamplerError(ValueError):
    pass


@dataclass(frozen=True)
class PlyProperty:
    name: str
    scalar_type: str
    byte_size: int


@dataclass(frozen=True)
class PlyHeader:
    path: Path
    format: str
    version: str
    vertex_count: int
    properties: tuple[PlyProperty, ...]
    comments: tuple[str, ...]
    header_lines: tuple[bytes, ...]
    header_bytes: int
    vertex_element_line: int
    record_size: int
    file_size: int
    mtime_ns: int

    @property
    def property_names(self) -> list[str]:
        return [prop.name for prop in self.properties]


@dataclass
class OutputState:
    count: int
    path: Path
    indices: list[int]
    index_set: set[int]
    handle: Any
    sha256: Any
    header_bytes: int
    records_written: int = 0


def splitmix64_priority(index: int, seed: int) -> int:
    """Return a deterministic 64-bit pseudorandom priority for an index."""
    value = ((index & MASK64) ^ (seed & MASK64))
    value = (value + GOLDEN64) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def select_nested_indices(total: int, counts: Iterable[int], seed: int) -> dict[int, list[int]]:
    normalized = sorted(set(counts))
    if not normalized or normalized[0] <= 0:
        raise PlySamplerError("Sample counts must be positive integers.")
    if normalized[-1] > total:
        raise PlySamplerError(f"Largest sample count {normalized[-1]} exceeds vertex count {total}.")

    largest = normalized[-1]
    heap: list[tuple[int, int]] = []
    for index in range(total):
        priority = splitmix64_priority(index, seed)
        item = (-priority, -index)
        if len(heap) < largest:
            heapq.heappush(heap, item)
            continue
        largest_selected = (-heap[0][0], -heap[0][1])
        if (priority, index) < largest_selected:
            heapq.heapreplace(heap, item)

    ranked = sorted((-negative_priority, -negative_index) for negative_priority, negative_index in heap)
    return {count: sorted(index for _, index in ranked[:count]) for count in normalized}


def read_ply_header(path: Path) -> PlyHeader:
    path = path.resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)

    header_lines: list[bytes] = []
    comments: list[str] = []
    properties: list[PlyProperty] = []
    ply_format: str | None = None
    version: str | None = None
    vertex_count: int | None = None
    vertex_element_line = -1
    current_element: str | None = None
    elements: list[str] = []

    with path.open("rb") as source:
        first = source.readline()
        header_lines.append(first)
        if first.strip() != b"ply":
            raise PlySamplerError("Input is not a PLY file.")
        while True:
            line_bytes = source.readline()
            if not line_bytes:
                raise PlySamplerError("Unexpected EOF before end_header.")
            header_lines.append(line_bytes)
            try:
                line = line_bytes.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise PlySamplerError("PLY header must be ASCII.") from exc
            if line == "end_header":
                break
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "format":
                if len(parts) != 3:
                    raise PlySamplerError("Malformed format declaration.")
                ply_format, version = parts[1], parts[2]
            elif parts[0] == "comment":
                comments.append(line[len("comment"):].lstrip())
            elif parts[0] == "element":
                if len(parts) != 3:
                    raise PlySamplerError("Malformed element declaration.")
                current_element = parts[1]
                elements.append(current_element)
                if current_element == "vertex":
                    if vertex_count is not None:
                        raise PlySamplerError("Multiple vertex elements are not supported.")
                    vertex_count = int(parts[2])
                    vertex_element_line = len(header_lines) - 1
            elif parts[0] == "property":
                if current_element != "vertex":
                    continue
                if len(parts) >= 2 and parts[1] == "list":
                    raise PlySamplerError("List properties in the vertex element are not supported.")
                if len(parts) != 3 or parts[1] not in PLY_SCALAR_SIZES:
                    raise PlySamplerError(f"Unsupported vertex property declaration: {line}")
                properties.append(PlyProperty(parts[2], parts[1], PLY_SCALAR_SIZES[parts[1]]))

        header_bytes = source.tell()

    if ply_format != "binary_little_endian":
        raise PlySamplerError(f"Only binary_little_endian PLY is supported, found: {ply_format}")
    if version is None or vertex_count is None or vertex_element_line < 0:
        raise PlySamplerError("PLY header is missing format or vertex element.")
    non_vertex_elements = [element for element in elements if element != "vertex"]
    if non_vertex_elements:
        raise PlySamplerError(
            "Non-vertex elements are explicitly rejected to avoid silently dropping data: "
            + ", ".join(non_vertex_elements)
        )
    if not properties:
        raise PlySamplerError("Vertex element has no scalar properties.")

    record_size = sum(prop.byte_size for prop in properties)
    stat = path.stat()
    expected_size = header_bytes + vertex_count * record_size
    if stat.st_size != expected_size:
        raise PlySamplerError(
            f"File size does not match a vertex-only fixed-record PLY: {stat.st_size} != {expected_size}."
        )
    return PlyHeader(
        path=path,
        format=ply_format,
        version=version,
        vertex_count=vertex_count,
        properties=tuple(properties),
        comments=tuple(comments),
        header_lines=tuple(header_lines),
        header_bytes=header_bytes,
        vertex_element_line=vertex_element_line,
        record_size=record_size,
        file_size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
    )


def output_header(header: PlyHeader, vertex_count: int) -> bytes:
    lines = list(header.header_lines)
    source_line = lines[header.vertex_element_line]
    newline = b"\r\n" if source_line.endswith(b"\r\n") else b"\n" if source_line.endswith(b"\n") else b""
    lines[header.vertex_element_line] = b"element vertex " + str(vertex_count).encode("ascii") + newline
    return b"".join(lines)


def index_digest(indices: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for index in indices:
        digest.update(struct.pack("<Q", index))
    return digest.hexdigest()


def count_label(count: int) -> str:
    return f"{count // 1000}k" if count >= 1000 and count % 1000 == 0 else str(count)


def infer_sh_order(property_names: Iterable[str]) -> tuple[int | None, int]:
    rest_count = sum(name.startswith("f_rest_") for name in property_names)
    if rest_count == 0:
        return 0, 0
    if rest_count % 3:
        return None, rest_count
    coefficients_per_channel = 1 + rest_count // 3
    root = math_isqrt(coefficients_per_channel)
    if root * root != coefficients_per_channel:
        return None, rest_count
    return root - 1, rest_count


def math_isqrt(value: int) -> int:
    # Local implementation keeps the sampler compatible with minimal Python builds.
    result = int(value ** 0.5)
    while (result + 1) * (result + 1) <= value:
        result += 1
    while result * result > value:
        result -= 1
    return result


def sample_ply(
    input_path: Path,
    output_dir: Path,
    counts: Iterable[int] = DEFAULT_COUNTS,
    seed: int = DEFAULT_SEED,
    block_records: int = DEFAULT_BLOCK_RECORDS,
    manifest_name: str = "dataset-manifest.json",
    command: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    header = read_ply_header(input_path)
    normalized_counts = sorted(set(int(count) for count in counts))
    selection_started = time.perf_counter()
    indices_by_count = select_nested_indices(header.vertex_count, normalized_counts, seed)
    selection_seconds = time.perf_counter() - selection_started

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = header.path.stem
    states: dict[int, OutputState] = {}
    for count in normalized_counts:
        output_path = output_dir / f"{base_name}-{count_label(count)}-seed{seed}.ply"
        indices = indices_by_count[count]
        generated_header = output_header(header, count)
        handle = output_path.open("wb")
        handle.write(generated_header)
        digest = hashlib.sha256()
        digest.update(generated_header)
        states[count] = OutputState(
            count=count,
            path=output_path,
            indices=indices,
            index_set=set(indices),
            handle=handle,
            sha256=digest,
            header_bytes=len(generated_header),
        )

    source_digest = hashlib.sha256()
    source_digest.update(b"".join(header.header_lines))
    write_started = time.perf_counter()
    largest_count = normalized_counts[-1]
    largest_state = states[largest_count]
    selected_pointer = 0
    block_bytes = block_records * header.record_size

    try:
        with header.path.open("rb") as source:
            source.seek(header.header_bytes)
            first_index = 0
            while first_index < header.vertex_count:
                records_in_block = min(block_records, header.vertex_count - first_index)
                expected_bytes = records_in_block * header.record_size
                block = source.read(expected_bytes)
                if len(block) != expected_bytes:
                    raise PlySamplerError(f"Short read while scanning vertex block at index {first_index}.")
                source_digest.update(block)
                block_end = first_index + records_in_block
                while selected_pointer < len(largest_state.indices):
                    source_index = largest_state.indices[selected_pointer]
                    if source_index >= block_end:
                        break
                    relative = source_index - first_index
                    start = relative * header.record_size
                    record = block[start:start + header.record_size]
                    for state in states.values():
                        if source_index in state.index_set:
                            state.handle.write(record)
                            state.sha256.update(record)
                            state.records_written += 1
                    selected_pointer += 1
                first_index = block_end
    finally:
        for state in states.values():
            state.handle.close()

    write_seconds = time.perf_counter() - write_started
    stat_after = header.path.stat()
    if stat_after.st_size != header.file_size or stat_after.st_mtime_ns != header.mtime_ns:
        raise PlySamplerError("Source PLY changed while sampling; outputs are not accepted as reproducible.")
    if selected_pointer != len(largest_state.indices):
        raise PlySamplerError("Not all selected source indices were written.")

    output_entries: list[dict[str, Any]] = []
    for count in normalized_counts:
        state = states[count]
        if state.records_written != count:
            raise PlySamplerError(f"Output {state.path} wrote {state.records_written} records, expected {count}.")
        expected_size = state.header_bytes + count * header.record_size
        actual_size = state.path.stat().st_size
        if actual_size != expected_size:
            raise PlySamplerError(f"Output size mismatch for {state.path}: {actual_size} != {expected_size}.")
        parsed_output = read_ply_header(state.path)
        if parsed_output.vertex_count != count:
            raise PlySamplerError(f"Output vertex count mismatch for {state.path}.")
        if parsed_output.properties != header.properties or parsed_output.comments != header.comments:
            raise PlySamplerError(f"Output header metadata changed unexpectedly for {state.path}.")
        output_entries.append(
            {
                "label": count_label(count).upper(),
                "path": state.path.relative_to(output_dir).as_posix(),
                "vertexCount": count,
                "bytes": actual_size,
                "sha256": state.sha256.hexdigest(),
                "selectedIndices": {
                    "minimum": state.indices[0],
                    "maximum": state.indices[-1],
                    "first16": state.indices[:16],
                    "last16": state.indices[-16:],
                    "sha256Uint64LE": index_digest(state.indices),
                },
                "headerBytes": state.header_bytes,
                "recordSize": header.record_size,
            }
        )

    subset_checks: list[dict[str, Any]] = []
    for smaller, larger in zip(normalized_counts, normalized_counts[1:]):
        index_subset = states[smaller].index_set < states[larger].index_set
        record_subset = verify_nested_output_records(states[smaller], states[larger], header.record_size)
        if not index_subset or not record_subset:
            raise PlySamplerError(f"Nested subset verification failed for {smaller} -> {larger}.")
        subset_checks.append(
            {
                "smallerCount": smaller,
                "largerCount": larger,
                "strictIndexSubset": index_subset,
                "rawRecordBytesMatch": record_subset,
                "method": "two-pointer comparison using recorded source indices and exact fixed-size record bytes",
            }
        )

    sh_order, f_rest_count = infer_sh_order(header.property_names)
    finished = time.perf_counter()
    manifest = {
        "manifestVersion": "1.0",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(header.path),
            "bytes": header.file_size,
            "sha256": source_digest.hexdigest(),
            "format": header.format,
            "plyVersion": header.version,
            "vertexCount": header.vertex_count,
            "headerBytes": header.header_bytes,
            "recordSize": header.record_size,
            "comments": list(header.comments),
            "properties": [
                {"name": prop.name, "type": prop.scalar_type, "bytes": prop.byte_size}
                for prop in header.properties
            ],
            "propertyCount": len(header.properties),
            "fRestCount": f_rest_count,
            "shOrder": sh_order,
            "nonVertexElements": [],
        },
        "sampling": {
            "algorithm": "splitmix64-priority-bottom-k-v1",
            "description": "Assign each source vertex a deterministic SplitMix64 priority from (index XOR seed); choose the lowest K priorities. Smaller outputs take prefixes of the same ranking.",
            "seed": seed,
            "withoutReplacement": True,
            "nested": True,
            "outputOrder": "ascending source vertex index",
            "blockRecords": block_records,
            "counts": normalized_counts,
        },
        "outputs": output_entries,
        "verification": {
            "sourceFileStableDuringRun": True,
            "headersReparsed": True,
            "propertiesAndCommentsPreserved": True,
            "fileSizesMatchFixedRecordLayout": True,
            "nestedSubsetChecks": subset_checks,
        },
        "performance": {
            "selectionWallSeconds": round(selection_seconds, 6),
            "scanWriteHashWallSeconds": round(write_seconds, 6),
            "totalWallSeconds": round(finished - started, 6),
            "peakRssBytes": None,
            "peakRssMethod": "unavailable: Python standard library on Windows does not provide reliable process peak RSS",
        },
        "provenance": {
            "tool": "tools/ply-sampler/sample_ply.py",
            "toolSha256": sha256_file(Path(__file__)),
            "python": sys.version,
            "command": command,
        },
        "license": {
            "status": "unknown",
            "redistribution": "not-cleared",
            "note": "The source data license and permission to redistribute derived subsets must be confirmed before publication.",
        },
    }
    manifest_path = output_dir / manifest_name
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_nested_output_records(smaller: OutputState, larger: OutputState, record_size: int) -> bool:
    larger_position = {source_index: output_index for output_index, source_index in enumerate(larger.indices)}
    with smaller.path.open("rb") as small_file, larger.path.open("rb") as large_file:
        small_file.seek(smaller.header_bytes)
        for small_output_index, source_index in enumerate(smaller.indices):
            small_file.seek(smaller.header_bytes + small_output_index * record_size)
            small_record = small_file.read(record_size)
            large_output_index = larger_position.get(source_index)
            if large_output_index is None:
                return False
            large_file.seek(larger.header_bytes + large_output_index * record_size)
            if small_record != large_file.read(record_size):
                return False
    return True


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            block = source.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def parse_counts(values: Iterable[str]) -> list[int]:
    counts: list[int] = []
    for value in values:
        normalized = value.strip().lower().replace("_", "")
        multiplier = 1
        if normalized.endswith("k"):
            multiplier = 1_000
            normalized = normalized[:-1]
        counts.append(int(normalized) * multiplier)
    return counts


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create deterministic nested subsets of a vertex-only binary little-endian PLY.")
    parser.add_argument("--input", required=True, help="Source binary_little_endian PLY.")
    parser.add_argument("--output-dir", required=True, help="Directory for sampled PLY files and dataset-manifest.json.")
    parser.add_argument("--counts", nargs="+", default=["10k", "250k"], help="Nested output counts. Default: 10k 250k.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Deterministic sampling seed. Default: {DEFAULT_SEED}.")
    parser.add_argument("--block-records", type=int, default=DEFAULT_BLOCK_RECORDS, help=f"Sequential scan block size in records. Default: {DEFAULT_BLOCK_RECORDS}.")
    parser.add_argument("--manifest-name", default="dataset-manifest.json", help="Manifest filename. Default: dataset-manifest.json.")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.block_records <= 0:
        raise SystemExit("--block-records must be positive.")
    counts = parse_counts(args.counts)
    command = " ".join([sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)])
    try:
        manifest = sample_ply(
            input_path=Path(args.input),
            output_dir=Path(args.output_dir),
            counts=counts,
            seed=args.seed,
            block_records=args.block_records,
            manifest_name=args.manifest_name,
            command=command,
        )
    except (OSError, PlySamplerError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "manifest": str((Path(args.output_dir) / args.manifest_name).resolve()),
        "sourceSha256": manifest["source"]["sha256"],
        "outputs": [{"path": output["path"], "vertexCount": output["vertexCount"], "sha256": output["sha256"]} for output in manifest["outputs"]],
        "performance": manifest["performance"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
