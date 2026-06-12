from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from convert_ply_to_w3gs import (  # noqa: E402
    PAYLOAD_PROFILES,
    PlyHeader,
    PlyProperty,
    PayloadWriter,
    SH3_REST_NAMES,
    input_sh_metadata,
    merge_splat_cluster,
    resolve_payload_profile,
    splat_from_values,
)


def header_with_rest(rest_names: list[str]) -> PlyHeader:
    names = [
        "x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", *rest_names,
        "opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3",
    ]
    return PlyHeader(Path("fixture.ply"), "binary_little_endian", 1, [PlyProperty(name, "float") for name in names], [], 0)


def values(seed: float = 0.0) -> dict[str, float]:
    result = {
        "x": seed, "y": seed + 1, "z": seed + 2,
        "f_dc_0": 0.1 + seed, "f_dc_1": 0.2 + seed, "f_dc_2": 0.3 + seed,
        "opacity": 0.0,
        "scale_0": 0.0, "scale_1": 0.0, "scale_2": 0.0,
        "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
    }
    result.update({name: index + seed for index, name in enumerate(SH3_REST_NAMES)})
    return result


class ConverterProfileTests(unittest.TestCase):
    def test_auto_selects_complete_sh3(self):
        self.assertEqual(resolve_payload_profile(header_with_rest(SH3_REST_NAMES), "auto").id, "raw-gaussian-sh3-v0")

    def test_auto_rejects_partial_sh3(self):
        with self.assertRaises(SystemExit):
            resolve_payload_profile(header_with_rest(SH3_REST_NAMES[:-1]), "auto")

    def test_explicit_sh0_allows_downcast(self):
        self.assertEqual(resolve_payload_profile(header_with_rest(SH3_REST_NAMES), "raw-gaussian-v0").id, "raw-gaussian-v0")

    def test_explicit_sh0_records_partial_input_as_downcast(self):
        header = header_with_rest(SH3_REST_NAMES[:-1])
        metadata = input_sh_metadata(header, PAYLOAD_PROFILES["raw-gaussian-v0"])
        self.assertEqual(metadata["inputShState"], "partial-or-nonstandard")
        self.assertIsNone(metadata["inputShDegree"])
        self.assertTrue(metadata["shDowncast"])
        self.assertEqual(metadata["ignoredShRestCount"], 44)

    def test_sh3_payload_is_236_bytes_and_preserves_order(self):
        profile = PAYLOAD_PROFILES["raw-gaussian-sh3-v0"]
        splat = splat_from_values(values(), profile)
        with tempfile.TemporaryDirectory() as temporary:
            writer = PayloadWriter(Path(temporary), 1, profile)
            chunk = writer.write_chunk("chunk", [splat])
            writer.close()
            payload = (Path(temporary) / chunk["uri"]).read_bytes()
        unpacked = profile.record_struct.unpack(payload)
        self.assertEqual(len(payload), 236)
        for actual, expected in zip(unpacked[11:14], splat.sh_dc):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(unpacked[14:59], splat.sh_rest):
            self.assertAlmostEqual(actual, expected)

    def test_parent_summary_averages_all_sh_coefficients(self):
        profile = PAYLOAD_PROFILES["raw-gaussian-sh3-v0"]
        first = splat_from_values(values(0.0), profile)
        second = splat_from_values(values(2.0), profile)
        merged, _, _ = merge_splat_cluster([first, second], [0, 1])
        self.assertEqual(len(merged.sh_rest), 45)
        self.assertAlmostEqual(merged.sh_dc[0], (first.sh_dc[0] + second.sh_dc[0]) / 2)
        self.assertAlmostEqual(merged.sh_rest[44], (first.sh_rest[44] + second.sh_rest[44]) / 2)


if __name__ == "__main__":
    unittest.main()
