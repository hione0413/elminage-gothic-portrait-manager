"""Headless sanity check for the DDS writer & image processing helpers."""
import struct
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portrait_manager import (  # noqa: E402
    LARGE_SIZE, SMALL_SIZE,
    auto_crop_head, fit_to_square, write_dds_rgba8,
)


def main() -> int:
    src = Image.new("RGBA", (640, 1024), (0, 0, 0, 0))
    # paint a simple pattern so we can verify pixel order
    for y in range(1024):
        for x in range(640):
            src.putpixel((x, y), (x % 256, y % 256, (x + y) % 256, 255))

    # Process
    large = fit_to_square(src, LARGE_SIZE)
    small = fit_to_square(auto_crop_head(src), SMALL_SIZE)
    assert large.size == (LARGE_SIZE, LARGE_SIZE), large.size
    assert small.size == (SMALL_SIZE, SMALL_SIZE), small.size

    # Write
    with tempfile.TemporaryDirectory() as td:
        big = Path(td) / "GR11_201.dds"
        sml = Path(td) / "GR10_201.dds"
        write_dds_rgba8(big, large)
        write_dds_rgba8(sml, small)

        big_bytes = big.read_bytes()
        sml_bytes = sml.read_bytes()

        # Header sanity
        assert big_bytes[:4] == b"DDS "
        (dw_size,) = struct.unpack_from("<I", big_bytes, 4)
        assert dw_size == 124, dw_size
        (dw_h,) = struct.unpack_from("<I", big_bytes, 12)
        (dw_w,) = struct.unpack_from("<I", big_bytes, 16)
        assert (dw_w, dw_h) == (LARGE_SIZE, LARGE_SIZE), (dw_w, dw_h)
        # PIXELFORMAT at offset 76. dwSize=32, flags @80, fourCC @84, bitCount @88
        (pf_size,) = struct.unpack_from("<I", big_bytes, 76)
        (pf_flags,) = struct.unpack_from("<I", big_bytes, 80)
        (pf_fourcc,) = struct.unpack_from("<I", big_bytes, 84)
        (pf_bits,) = struct.unpack_from("<I", big_bytes, 88)
        (mr,) = struct.unpack_from("<I", big_bytes, 92)
        (mg,) = struct.unpack_from("<I", big_bytes, 96)
        (mb,) = struct.unpack_from("<I", big_bytes, 100)
        (ma,) = struct.unpack_from("<I", big_bytes, 104)
        assert pf_size == 32, pf_size
        assert pf_flags == 0x41, hex(pf_flags)  # RGB | ALPHA
        assert pf_fourcc == 0
        assert pf_bits == 32
        assert (mr, mg, mb, ma) == (0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000)

        # Body length
        expected_big = LARGE_SIZE * LARGE_SIZE * 4
        expected_sml = SMALL_SIZE * SMALL_SIZE * 4
        assert len(big_bytes) - 128 == expected_big, len(big_bytes)
        assert len(sml_bytes) - 128 == expected_sml, len(sml_bytes)

        # Round-trip via Pillow's DDS reader
        for p, expect in [(big, (LARGE_SIZE, LARGE_SIZE)), (sml, (SMALL_SIZE, SMALL_SIZE))]:
            with Image.open(p) as im:
                im.load()
                assert im.size == expect, (p.name, im.size, expect)

    print("OK - smoketest passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
