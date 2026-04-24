# Verdi `.rc` Parsing

Synopsys Verdi's signal-save file (often called a `.rc` or `.f` for signal lists, or exported via `Save Signal List As`) is used to restore signal groups and radices in nWave. The file is text, and although the exact format varies between Verdi versions and export styles, the parser handles the common shapes.

## Recognized entries

The parser extracts signal lines and group markers from any of these forms:

### 1. `wvAddSignal -win <win> <signal>` (nWave command style)
```
wvAddSignal -win $_nWave1 "/tb/u_dut/u_axi/awvalid"
wvAddSignal -win $_nWave1 -colorIdx 4 "/tb/u_dut/u_axi/awaddr"
```

### 2. Group markers
```
wvOpenGroup "AXI_WR"
wvAddSignal ...
wvCloseGroup
```
Signals between `wvOpenGroup "<name>"` and the matching `wvCloseGroup` are assigned to group `<name>`.

### 3. Radix hints
```
wvSetRadix -win $_nWave1 -signal {/tb/u_dut/u_axi/awaddr} hex
```

### 4. Plain signal lists
Lines that look like hierarchical paths (slash or dot-separated) and are not commands are treated as signals in the current group (default group: `default`).

### 5. Comments
Lines starting with `#` are skipped.

## Parsed output

```json
{
  "groups": {
    "AXI_WR": {
      "signals": [
        { "hier": "tb.u_dut.u_axi.awvalid", "radix": "hex" },
        { "hier": "tb.u_dut.u_axi.awaddr",  "radix": "hex" }
      ]
    },
    "default": {
      "signals": [ ... ]
    }
  }
}
```

Slash-separated hierarchies from Verdi (`/tb/u_dut/...`) are normalized to dot-separated (`tb.u_dut....`) to match VCD/SV-sim conventions.

## Usage

```
scripts/rc_parse.py <rc_file> --format json [--group <name>] [--flatten]
```

- `--group <name>` → return only the signals of that group.
- `--flatten` → return just the signal list (one per line) for easy piping into `vcd_window.py --signals -`.

## Interface matching

To pick the `.rc` group that matches the failure's interface:
1. Lowercase the failure's interface keyword (`axi`, `apb`, `ddr`, `noc`, custom).
2. Find `.rc` groups whose name contains that keyword (substring match).
3. If multiple match, union them.
4. If none match, return the `default` group plus a warning that no group matched.
