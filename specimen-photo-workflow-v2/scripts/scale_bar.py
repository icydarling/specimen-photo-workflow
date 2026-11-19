#!/usr/bin/env python3
"""Calculate a scale bar from measured original-image intervals; never edits images."""

import argparse
import json
import math
import statistics
from pathlib import Path


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Value must be finite and positive")
    return number


def interval(value):
    try:
        values = [float(part) for part in value.split(",")]
        if len(values) != 5 or not all(math.isfinite(v) for v in values):
            raise ValueError
        x1, y1, x2, y2, length_mm = values
        pixels = math.hypot(x2 - x1, y2 - y1)
        if pixels <= 0 or not math.isfinite(pixels) or length_mm <= 0:
            raise ValueError
        q = pixels / length_mm
        if not math.isfinite(q) or q <= 0:
            raise ValueError
        return {"start_px": [x1, y1], "end_px": [x2, y2],
                "length_mm": length_mm, "length_px": pixels, "px_per_mm": q}
    except (ValueError, OverflowError):
        raise argparse.ArgumentTypeError(
            "Interval must be x1,y1,x2,y2,length_mm with distinct finite endpoints and positive mm"
        ) from None


def calculate(intervals, scales, bar_mm, spread_warning=0.01):
    q_values = [item["px_per_mm"] for item in intervals]
    q = statistics.median(q_values)
    spread = (max(q_values) - min(q_values)) / q
    scale = math.prod(scales)
    q_final = q * scale
    expected = bar_mm * q_final
    if not all(math.isfinite(n) and n > 0 for n in (scale, q_final, expected)):
        raise ValueError("Combined scale and bar length must remain finite and positive")
    bar_pixels = math.floor(expected + 0.5)
    if bar_pixels < 1:
        raise ValueError("Scale bar rounds to zero pixels; increase bar length or output scale")
    rounding_error = bar_pixels - expected
    warnings = []
    if len(intervals) < 3:
        warnings.append("Fewer than three intervals: remeasure other clear ruler sections")
    if spread > spread_warning:
        warnings.append("Interval scale spread exceeds review threshold; investigate before use")
    if abs(rounding_error) / expected > 0.01:
        warnings.append("Rounding changes bar length by more than 1%; use a longer bar or larger output")
    return {
        "status": "arithmetic_only",
        "limitations": "Units, endpoints, shared image coordinates, imaging plane, transform evidence and exported bar are not verified",
        "intervals": intervals,
        "aggregation": "median of per-interval px/mm; raw intervals retained",
        "source_px_per_mm": q,
        "interval_relative_spread": spread,
        "spread_review_threshold": spread_warning,
        "scale_factors": scales,
        "cumulative_isotropic_scale": scale,
        "final_px_per_mm": q_final,
        "bar_mm": bar_mm,
        "bar_px_exact": expected,
        "bar_px_rounded": bar_pixels,
        "rounding_error_px": rounding_error,
        "rounding_relative_error": abs(rounding_error) / expected,
        "exported_bar_px_measured": None,
        "imaging_plane_verified": False,
        "visual_inspection_complete": False,
        "warnings": warnings,
    }


def qualify(result, units=False, endpoints=False, plane=False, transform=False,
            evidence_note='', measured_bar_px=None, export_tolerance_px=1):
    if not math.isfinite(export_tolerance_px) or export_tolerance_px < 0:
        raise ValueError('Export tolerance must be finite and nonnegative')
    evidence = dict(units=units, endpoints=endpoints, plane=plane, transform=transform)
    reasons = ['Evidence not verified: '+k for k,v in evidence.items() if not v]
    if not evidence_note.strip():
        reasons.append('Missing calibration evidence note')
    reasons.extend(result['warnings'])
    state = 'pending_review' if reasons else 'ready_for_drawing'
    delta = None
    if measured_bar_px is not None:
        if not math.isfinite(measured_bar_px) or measured_bar_px <= 0:
            raise ValueError('Measured exported bar must be finite and positive')
        delta = measured_bar_px-result['bar_px_rounded']
        if abs(delta) > export_tolerance_px:
            reasons.append('Exported bar differs from planned integer line length')
            state = 'pending_review'
        elif not reasons:
            state = 'export_verified'
    result.update(calibration_status=state, evidence_verified=evidence,
                  evidence_note=evidence_note, review_reasons=reasons,
                  exported_bar_px_measured=measured_bar_px,
                  exported_bar_error_px=delta, export_tolerance_px=export_tolerance_px,
                  imaging_plane_verified=bool(plane),
                  evidence_validation='caller_assertions_not_image_recognition')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=interval, action="append", required=True,
                        help="Original-image x1,y1,x2,y2,known_length_mm; repeat for independent sections")
    parser.add_argument("--scale", type=positive, action="append", required=True,
                        help="Isotropic scale factor, e.g. 0.25 for 25%%; repeat to multiply; use 1 for crop only")
    parser.add_argument("--bar-mm", type=positive, required=True, help="Bar label in mm (20 cm = 200 mm)")
    parser.add_argument("--spread-warning", type=positive, default=0.01,
                        help="Relative interval-spread review threshold (default 0.01; not an accuracy guarantee)")
    parser.add_argument("--source-id", default="unspecified", help="Sample or source identifier; not proof of provenance")
    parser.add_argument("--output", type=Path, help="New JSON record; existing files are not overwritten")
    parser.add_argument('--units-verified', action='store_true')
    parser.add_argument('--endpoints-verified', action='store_true')
    parser.add_argument('--plane-verified', action='store_true')
    parser.add_argument('--transform-verified', action='store_true')
    parser.add_argument('--evidence-note', default='')
    parser.add_argument('--measured-bar-px', type=positive)
    parser.add_argument('--export-tolerance-px', type=float, default=1)
    args = parser.parse_args()
    try:
        result = calculate(args.interval, args.scale, args.bar_mm, args.spread_warning)
        qualify(result, args.units_verified, args.endpoints_verified, args.plane_verified,
                args.transform_verified, args.evidence_note, args.measured_bar_px,
                args.export_tolerance_px)
        result["source_id"] = args.source_id
        serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(serialized)
        print(serialized, end="")
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
