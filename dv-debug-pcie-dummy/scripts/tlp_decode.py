#!/usr/bin/env python3
"""
tlp_decode.py — DEMO TLP header decoder.

Decodes the first DW of a PCIe TLP header from a hex string. Shown as an
example of a domain-specific helper script that the SKILL.md can invoke
when the generic parent tools aren't enough.

Real skill would support multi-DW headers, vendor-specific TLPs, and
parse from VCD value-change blobs directly.

Usage:
    tlp_decode.py --dw0 0x40000001
"""
from __future__ import annotations
import argparse, json, sys

# Minimal FMT/TYPE decode table (not exhaustive)
FMT_NAMES = {
    0b000: "3DW_no_data",
    0b001: "4DW_no_data",
    0b010: "3DW_with_data",
    0b011: "4DW_with_data",
    0b100: "prefix_TLP",
}

TYPE_NAMES = {
    (0b000, 0b00000): "MRd_3DW",
    (0b001, 0b00000): "MRd_4DW",
    (0b010, 0b00000): "MWr_3DW",
    (0b011, 0b00000): "MWr_4DW",
    (0b000, 0b01010): "CplD",
    (0b010, 0b01010): "CplD_with_data",
    (0b000, 0b00100): "CfgRd0",
    (0b010, 0b00100): "CfgWr0",
}


def decode(dw0: int) -> dict:
    fmt = (dw0 >> 29) & 0b111
    type_ = (dw0 >> 24) & 0b11111
    length = dw0 & 0x3FF
    tc = (dw0 >> 20) & 0b111
    th = (dw0 >> 16) & 0b1
    td = (dw0 >> 15) & 0b1
    ep = (dw0 >> 14) & 0b1
    attr = (dw0 >> 12) & 0b11
    at = (dw0 >> 10) & 0b11

    return {
        "fmt":          f"0b{fmt:03b}",
        "fmt_name":     FMT_NAMES.get(fmt, "UNKNOWN_FMT"),
        "type":         f"0b{type_:05b}",
        "type_name":    TYPE_NAMES.get((fmt, type_), "UNKNOWN_TYPE"),
        "length_dw":    length,
        "tc":           tc,
        "th":           th,
        "td":           td,
        "ep_poisoned":  bool(ep),
        "attr":         f"0b{attr:02b}",
        "at":           f"0b{at:02b}",
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dw0", required=True, help="First DW as 0x… hex")
    args = ap.parse_args(argv)
    dw0 = int(args.dw0, 16)
    print(json.dumps(decode(dw0), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
