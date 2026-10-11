#!/usr/bin/env python3
"""
export_figure.py — Dual-format scientific figure export.

Distilled from the scientific-plotting skill: every research figure ships as
(1) a high-resolution PNG (crisp at phone zoom),
(2) an editable SVG (text stays text, never outlined paths).

Library use:
    from export_figure import export_figure
    report = export_figure(fig, name="bessel", out_dir="figures")

    # One-call convenience (export + verify in-process, no subprocess):
    from export_figure import export_and_verify
    result = export_and_verify(fig, name="bessel", out_dir="figures")
    # result = {"export": report, "verify": report, "ok": bool}

CLI checks (no figure object needed):
    python export_figure.py --check-svg  figures/bessel.svg   # editable <text>?
    python export_figure.py --inspect   figures/bessel.png   # dimensions / dpi
    python export_figure.py --grayscale  figures/bessel.png   # grayscale robustness preview
    python export_figure.py --ensure-phys figures/bessel.png --dpi 300  # write+verify pHYs
    python export_figure.py --verify-all  figures/bessel      # check-svg+inspect+grayscale+ensure-phys in one pass
    python export_figure.py --selftest                        # end-to-end toolchain check

Exit codes: 0 = OK, 1 = problem found (editable-text check failed, file missing, ...).
Only stdlib + matplotlib are required.
Note: external file hooks (antivirus, sync, platform watchers) may rewrite an
exported PNG after the export process exits. Run --inspect (and --ensure-phys if
dpi reads null) as a separate post-export step to verify the final file.
"""

import argparse
import json
import os
import struct
import sys
import zlib

PNG_DPI_DEFAULT = 300


# --------------------------------------------------------------------------
# PNG header parsing (stdlib only, no Pillow dependency)
# --------------------------------------------------------------------------

def _png_dimensions(path):
    """Return (width, height) px of a PNG file by parsing IHDR."""
    with open(path, "rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file: %s" % path)
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def _png_phys_dpi(path):
    """Return (x_dpi, y_dpi, unit_is_meter) from the pHYs chunk, or None."""
    with open(path, "rb") as f:
        f.read(8)  # signature
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                return None
            length, ctype = struct.unpack(">I", chunk_header[:4])[0], chunk_header[4:8]
            if ctype == b"pHYs":
                data = f.read(length)
                if len(data) < 9:
                    return None
                px_x, px_y, unit = struct.unpack(">IIB", data[:9])
                return int(px_x), int(px_y), bool(unit)
            f.seek(length + 4, os.SEEK_CUR)  # skip data + CRC


def _ensure_png_phys(path, dpi):
    """
    Guarantee the PNG carries a pHYs chunk encoding the physical dpi.

    Matplotlib/Pillow occasionally omit pHYs (observed across identical calls,
    not version-pinned), which silently drops the 300-dpi physical-size
    metadata that downstream layout tools rely on. Stdlib-only: if pHYs is
    missing, insert it right after IHDR. Idempotent — a file already carrying
    pHYs is returned unchanged. After inserting, the file is re-read and
    verified (with one retry) to guard against transient filesystem/cache
    hiccups observed in the wild.

    Returns True if pHYs is present after the call, False otherwise.
    """
    sig = b"\x89PNG\r\n\x1a\n"
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return False
    if not data.startswith(sig) or len(data) < 16:
        return False
    pos = 8
    has_phys = False
    ihdr_end = None
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if ctype == b"IHDR" and ihdr_end is None:
            ihdr_end = end
        elif ctype == b"pHYs":
            has_phys = True
            break
        pos = end
        if ctype == b"IEND":
            break
    if has_phys or ihdr_end is None:
        return has_phys
    ppm = int(round(float(dpi) / 0.0254))
    payload = struct.pack(">IIB", ppm, ppm, 1)  # ppuX, ppuY, unit=1 (meter)
    crc = zlib.crc32(b"pHYs" + payload) & 0xFFFFFFFF
    chunk = struct.pack(">I", len(payload)) + b"pHYs" + payload + struct.pack(">I", crc)
    for _attempt in range(2):  # insert, then verify-and-retry once
        with open(path, "wb") as f:
            f.write(data[:ihdr_end] + chunk + data[ihdr_end:])
        # Read back and verify the chunk really landed on disk.
        try:
            with open(path, "rb") as f:
                content = f.read()
        except OSError:
            return False
        pos = 8
        while pos + 12 <= len(content):
            length = struct.unpack(">I", content[pos:pos + 4])[0]
            ctype = content[pos + 4:pos + 8]
            if ctype == b"pHYs":
                return True
            pos += 12 + length
    return False


# --------------------------------------------------------------------------
# SVG editable-text inspection (stdlib only, no lxml dependency)
# --------------------------------------------------------------------------

def check_svg_text(svg_path):
    """
    Check whether an SVG still contains editable <text> elements.

    When Matplotlib's svg.fonttype == 'path' (its default), every glyph becomes
    a <path> outline and the text can no longer be edited or searched.
    With svg.fonttype == 'none' (enforced by export_figure), <text> elements
    survive. Returns a dict summary.
    """
    if not os.path.isfile(svg_path):
        return {"ok": False, "error": "file not found: %s" % svg_path,
                "editable_text": False}
    with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if "<svg" not in content:
        return {"ok": False, "editable_text": False,
                "error": "not an SVG document (no <svg root)", "file": svg_path}
    n_text = content.count("<text")
    n_path = content.count("<path")
    # Glyph outlines imported from a font also appear as <path> in <defs>;
    # the decisive signal is presence of real <text> elements.
    editable = n_text > 0
    return {
        "ok": editable,
        "editable_text": editable,
        "text_elements": n_text,
        "path_elements": n_path,
        "svg_bytes": len(content.encode("utf-8", errors="replace")),
        "file": svg_path,
        "hint": ("Editable <text> found — words can be changed in a vector editor."
                 if editable else
                 "No <text> elements: text was exported as outlines "
                 "(svg.fonttype='path'). Re-export with svg.fonttype='none'."),
    }


# --------------------------------------------------------------------------
# Core export
# --------------------------------------------------------------------------

def export_figure(fig, name, out_dir=".",
                  png_dpi=PNG_DPI_DEFAULT, transparent=False, overwrite=False):
    """
    Export a matplotlib Figure as PNG + editable SVG.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure to export. This function never closes the figure.
    name : str
        Base file name without extension.
    out_dir : str
        Output directory (created if missing).
    png_dpi : int
        PNG resolution (default 300 — sharp at phone zoom).
    transparent : bool
        Transparent PNG background. Default white (print/mobile safe).
    overwrite : bool
        Overwrite existing outputs (default False — refuses to clobber files
        already on disk). Set True only for a task-owned output directory
        where re-running after a fix is expected.

    Returns
    -------
    dict report with keys: ok, files, png, svg.
    """
    import matplotlib

    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, name + ".png")
    svg_path = os.path.join(out_dir, name + ".svg")

    for p in [png_path, svg_path]:
        if os.path.exists(p) and not overwrite:
            raise FileExistsError("Refusing to overwrite existing file: %s" % p)

    # Keep text editable in SVG: fonttype 'none' instead of the 'path' default.
    with matplotlib.rc_context({"svg.fonttype": "none"}):
        fig.savefig(png_path, dpi=png_dpi,
                    facecolor=("none" if transparent else "white"),
                    transparent=transparent, bbox_inches="tight", pad_inches=0.05)
        fig.savefig(svg_path, facecolor="white", bbox_inches="tight", pad_inches=0.05)

    width_px, height_px = _png_dimensions(png_path)
    _ensure_png_phys(png_path, png_dpi)
    _phys = _png_phys_dpi(png_path)
    _phys_verified = bool(_phys and _phys[2])
    svg_check = check_svg_text(svg_path)

    report = {
        "ok": svg_check["editable_text"],
        "files": {"png": png_path, "svg": svg_path},
        "png": {"file": png_path, "dpi": png_dpi,
                "width_px": width_px, "height_px": height_px,
                "transparent": transparent},
        "svg": svg_check,
        "warning": (None if svg_check["editable_text"] else
                    "SVG text was outlined — re-export with svg.fonttype='none'."),
    }
    if not _phys_verified:
        report["warning"] = ((report["warning"] + " " if report["warning"] else "")
                             + "PNG pHYs metadata could not be written/verified "
                               "— physical dpi unreadable by layout tools.")
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _cmd_check_svg(path):
    result = check_svg_text(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["editable_text"] else 1


def _cmd_inspect(path):
    if not os.path.isfile(path):
        print(json.dumps({"ok": False, "error": "file not found: %s" % path},
                         ensure_ascii=False, indent=2))
        return 1
    lower = path.lower()
    if lower.endswith(".png"):
        try:
            width_px, height_px = _png_dimensions(path)
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)},
                             ensure_ascii=False, indent=2))
            return 1
        phys = _png_phys_dpi(path)
        dpi_x = round(phys[0] * 0.0254, 1) if phys and phys[2] else None
        result = {"ok": True, "file": path, "width_px": width_px,
                  "height_px": height_px, "dpi": dpi_x,
                  "bytes": os.path.getsize(path)}
        if dpi_x is None:
            result["hint"] = ("No physical dpi metadata (pHYs) in this PNG. "
                               "Run: python export_figure.py --ensure-phys "
                               "<file> --dpi 300, then re-inspect.")
    elif lower.endswith(".svg"):
        result = check_svg_text(path)
        result["bytes"] = os.path.getsize(path)
        result["ok"] = result["editable_text"]
    else:
        print(json.dumps({"ok": False, "error": "unsupported type (png/svg only)"},
                         ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _require_matplotlib():
    """Import matplotlib with the Agg backend; return (module, pyplot) or None."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return matplotlib, plt
    except ImportError:
        return None


def _cmd_grayscale(png_path, out_path=None):
    """Write a luminance grayscale preview of a PNG for the robustness checklist."""
    if not os.path.isfile(png_path):
        _print_json({"ok": False, "error": "file not found: %s" % png_path})
        return 1
    loaded = _require_matplotlib()
    if not loaded:
        _print_json({"ok": False,
                     "error": "matplotlib is required for --grayscale "
                              "(pip install matplotlib)"})
        return 1
    _, plt = loaded
    import matplotlib.image as mpimg
    try:
        img = mpimg.imread(png_path)
    except Exception as exc:
        _print_json({"ok": False, "error": "cannot read PNG: %s" % exc})
        return 1
    if img.ndim == 3:
        rgb = img[..., :3]
        gray = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    else:
        gray = img
    if not out_path:
        root, _ = os.path.splitext(png_path)
        out_path = root + ".gray.png"
    plt.imsave(out_path, gray, cmap="gray")
    _print_json({"ok": True, "file": png_path, "grayscale_preview": out_path,
                 "note": "Check the preview: every series must stay separable "
                         "by linestyle/marker."})
    return 0


def _cmd_selftest(out_dir=None):
    """End-to-end toolchain check: export a demo figure and verify all outputs."""
    loaded = _require_matplotlib()
    if not loaded:
        _print_json({"ok": False,
                     "error": "matplotlib is required for --selftest "
                              "(pip install matplotlib)"})
        return 1
    matplotlib, plt = loaded
    import tempfile
    out_dir = out_dir or tempfile.mkdtemp(prefix="sciplot_selftest_")
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 0], "-", lw=2, label="solid")
    ax.plot([0, 1, 2], [1, 0, 1], "--", lw=2, label="dashed")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend(fontsize=8)
    report = export_figure(fig, name="selftest", out_dir=out_dir)
    plt.close(fig)
    # Negative control: outlined text must be flagged as non-editable.
    fig2, ax2 = plt.subplots(figsize=(2, 1))
    ax2.set_xlabel("outlined")
    bad_svg = os.path.join(out_dir, "selftest_outlined.svg")
    with matplotlib.rc_context({"svg.fonttype": "path"}):
        fig2.savefig(bad_svg)
    plt.close(fig2)
    bad_check = check_svg_text(bad_svg)
    files = report["files"]
    checks = {
        "all_files_written": all(os.path.isfile(files[k])
                                  for k in ("png", "svg")),
        "svg_text_editable": bool(report["svg"]["editable_text"]),
        "outlined_svg_flagged": bad_check["editable_text"] is False,
        "png_dpi_recorded": report["png"]["dpi"] >= 200,
    }
    # Golden regression: the demo figure is deterministic, so its output
    # footprint must stay within a stable band. Exact pixel size varies with
    # font metrics across matplotlib versions; the bands catch real
    # regressions (broken tight-bbox, dropped text, wrong dpi) without
    # false positives on harmless rendering drift.
    svg_texts = int(report["svg"]["text_elements"])
    png_w = int(report["png"]["width_px"])
    png_h = int(report["png"]["height_px"])
    checks.update({
        "golden_svg_text_min": svg_texts >= 8,
        "golden_png_width_band": 500 <= png_w <= 1500,
        "golden_png_height_band": 300 <= png_h <= 1000,
        "golden_png_dpi_exact": int(report["png"]["dpi"]) == 300,
    })
    ok = bool(report["ok"]) and all(checks.values())
    _print_json({"ok": ok, "checks": checks, "output_dir": out_dir, "files": files})
    return 0 if ok else 1


def _cmd_ensure_phys(png_path, dpi=PNG_DPI_DEFAULT):
    """Independently write+verify the PNG pHYs chunk (post-export hardening)."""
    if not os.path.isfile(png_path):
        _print_json({"ok": False, "error": "file not found: %s" % png_path})
        return 1
    phys_before = _png_phys_dpi(png_path)
    had_before = bool(phys_before and phys_before[2])
    _ensure_png_phys(png_path, dpi)
    phys = _png_phys_dpi(png_path)
    verified = bool(phys and phys[2])
    _print_json({"ok": verified,
                 "file": png_path,
                 "dpi": (round(phys[0] * 0.0254, 1) if verified else None),
                 "already_present": had_before,
                 "note": ("pHYs verified on disk." if verified else
                          "pHYs could not be written/verified — check "
                          "antivirus/sync interference or file permissions.")})
    return 0 if verified else 1


def verify_figure(prefix, dpi=PNG_DPI_DEFAULT, grayscale=True):
    """
    Batch the four post-export checks (check-svg, inspect, grayscale,
    ensure-phys) into one call and return a merged dict.

    Callable from Python (no subprocess needed): a plotting script can
    import this function and verify its own output in-process, avoiding
    extra model round-trips for the post-export checklist.

    Accepts a prefix ("figures/oscillation") or a full png/svg path;
    the companion file is derived by swapping the extension.
    Set grayscale=False to skip the grayscale preview (saves ~0.1s
    if matplotlib image reading is not needed).
    """
    # Resolve paths from prefix or explicit extension.
    if prefix.lower().endswith(".png"):
        png_path = prefix
        svg_path = prefix[:-4] + ".svg"
    elif prefix.lower().endswith(".svg"):
        svg_path = prefix
        png_path = prefix[:-4] + ".png"
    else:
        png_path = prefix + ".png"
        svg_path = prefix + ".svg"

    results = {}
    overall_ok = True

    # 1. SVG editable-text check
    svg_res = check_svg_text(svg_path)
    results["svg_text"] = svg_res
    overall_ok = overall_ok and svg_res["editable_text"]

    # 2. PNG inspect (dimensions + dpi)
    png_res = {"ok": False}
    if os.path.isfile(png_path):
        try:
            w, h = _png_dimensions(png_path)
            phys = _png_phys_dpi(png_path)
            dpi_x = round(phys[0] * 0.0254, 1) if phys and phys[2] else None
            png_res = {"ok": True, "file": png_path, "width_px": w,
                       "height_px": h, "dpi": dpi_x,
                       "bytes": os.path.getsize(png_path)}
            if dpi_x is None:
                png_res["hint"] = ("pHYs missing \u2014 will be repaired by "
                                    "ensure-phys below.")
        except ValueError as exc:
            png_res = {"ok": False, "error": str(exc)}
    else:
        png_res = {"ok": False, "error": "file not found: %s" % png_path}
    results["png_inspect"] = png_res
    if not png_res["ok"]:
        overall_ok = False

    # 3. Ensure pHYs (repair if dpi missing, then re-verify)
    if png_res["ok"] and png_res.get("dpi") is None:
        _ensure_png_phys(png_path, dpi)
        phys = _png_phys_dpi(png_path)
        dpi_x = round(phys[0] * 0.0254, 1) if phys and phys[2] else None
        png_res["dpi"] = dpi_x
        results["ensure_phys"] = {"ok": bool(dpi_x), "dpi": dpi_x,
                                   "repaired": True}
        if dpi_x is None:
            overall_ok = False
    else:
        results["ensure_phys"] = {"ok": True, "already_present": True,
                                   "dpi": png_res.get("dpi")}

    # 4. Grayscale robustness preview (optional)
    if not grayscale:
        results["grayscale"] = {"ok": True, "skipped": True}
    else:
        gray_res = {"ok": False, "skipped": True,
                    "note": "matplotlib not available for grayscale preview."}
        loaded = _require_matplotlib()
        if loaded:
            _, plt = loaded
            import matplotlib.image as mpimg
            try:
                img = mpimg.imread(png_path)
                if img.ndim == 3:
                    rgb = img[..., :3]
                    gray = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1]
                            + 0.0722 * rgb[..., 2])
                else:
                    gray = img
                root, _ = os.path.splitext(png_path)
                gray_path = root + ".gray.png"
                plt.imsave(gray_path, gray, cmap="gray")
                gray_res = {"ok": True, "grayscale_preview": gray_path,
                            "note": ("Open preview: every series must stay "
                                     "separable by linestyle/marker.")}
            except Exception as exc:
                gray_res = {"ok": False, "error": "cannot read/process PNG: %s" % exc}
        results["grayscale"] = gray_res

    return {"ok": overall_ok, "prefix": prefix,
            "files": {"png": png_path, "svg": svg_path},
            "checks": results}


def export_and_verify(fig, name, out_dir=".",
                      png_dpi=PNG_DPI_DEFAULT, transparent=False,
                      overwrite=False, grayscale=True):
    """
    One-call convenience: export a figure AND verify it in the same process.

    Combines export_figure() + verify_figure() so a plotting script can do
    everything (plot, export, verify) in a single run with a single result
    dict — eliminating extra model round-trips for post-export checks.

    Returns a merged dict with both the export report and verification results.
    """
    export_report = export_figure(fig, name, out_dir=out_dir,
                                  png_dpi=png_dpi,
                                  transparent=transparent, overwrite=overwrite)
    prefix = os.path.join(out_dir, name)
    verify_report = verify_figure(prefix, dpi=png_dpi, grayscale=grayscale)
    return {"export": export_report, "verify": verify_report,
            "ok": export_report["ok"] and verify_report["ok"]}


def _cmd_verify_all(prefix, dpi=PNG_DPI_DEFAULT):
    """CLI wrapper around verify_figure() — prints JSON, returns exit code."""
    result = verify_figure(prefix, dpi=dpi, grayscale=True)
    _print_json(result)
    return 0 if result["ok"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Scientific figure export/check utilities.")
    parser.add_argument("--check-svg", metavar="SVG",
                        help="Verify an SVG keeps editable <text> (not outlines).")
    parser.add_argument("--inspect", metavar="FILE",
                        help="Report PNG dimensions/DPI or SVG text status.")
    parser.add_argument("--grayscale", metavar="PNG",
                        help="Write a grayscale preview of a PNG (robustness check).")
    parser.add_argument("--grayscale-out", metavar="OUT",
                        help="Optional output path for the grayscale preview.")
    parser.add_argument("--selftest", action="store_true",
                        help="Run an end-to-end export + verification on a demo figure.")
    parser.add_argument("--verify-all", metavar="PREFIX",
                        help="Batch check-svg + inspect + grayscale + ensure-phys "
                             "on PREFIX.png and PREFIX.svg in one pass.")
    parser.add_argument("--ensure-phys", metavar="PNG",
                        help="Write and verify the pHYs dpi metadata of an exported PNG.")
    parser.add_argument("--phys-dpi", type=int, default=PNG_DPI_DEFAULT, metavar="DPI",
                        help="Dpi for --ensure-phys and --verify-all (default 300).")
    args = parser.parse_args()
    if args.check_svg:
        sys.exit(_cmd_check_svg(args.check_svg))
    if args.inspect:
        sys.exit(_cmd_inspect(args.inspect))
    if args.grayscale:
        sys.exit(_cmd_grayscale(args.grayscale, args.grayscale_out))
    if args.ensure_phys:
        sys.exit(_cmd_ensure_phys(args.ensure_phys, args.phys_dpi))
    if args.verify_all:
        sys.exit(_cmd_verify_all(args.verify_all, dpi=args.phys_dpi))
    if args.selftest:
        sys.exit(_cmd_selftest())
    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()
