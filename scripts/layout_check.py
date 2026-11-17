"""Check measured specimen bounds; never reads or edits images."""
import argparse
import json
import math


def box(value, name):
    if len(value) != 4 or not all(math.isfinite(x) for x in value):
        raise ValueError(name + ' needs four finite coordinates')
    if value[2] <= value[0] or value[3] <= value[1]:
        raise ValueError(name + ' needs positive width and height')
    return list(value)


def inside(b, r):
    return b[0] >= r[0] and b[1] >= r[1] and b[2] <= r[2] and b[3] <= r[3]


def check(canvas, bbox, region=None, safe_bbox=None, tolerance=1):
    if len(canvas) != 2 or not all(math.isfinite(x) and x > 0 for x in canvas):
        raise ValueError('canvas must have finite positive dimensions')
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('tolerance must be finite and nonnegative')
    frame = [0, 0, *canvas]
    r = box(region if region is not None else frame, 'region')
    b = box(bbox, 'bbox')
    safe = box(safe_bbox if safe_bbox is not None else b, 'safe_bbox')
    if not inside(r, frame) or not inside(b, safe):
        raise ValueError('region must fit canvas; safe_bbox must contain bbox')
    error = [(b[0]+b[2]-r[0]-r[2])/2, (b[1]+b[3]-r[1]-r[3])/2]
    move = [math.floor(-x+0.5) for x in error]
    shifted = [safe[i]+move[i % 2] for i in range(4)]
    return {'status': 'geometry_only', 'canvas': canvas, 'region': r,
            'bbox': b, 'safe_bbox': safe, 'tolerance_px': tolerance,
            'margins_px': [b[0]-r[0], b[1]-r[1], r[2]-b[2], r[3]-b[3]],
            'center_error_px': error,
            'relative_center_error': [error[0]/(r[2]-r[0]), error[1]/(r[3]-r[1])],
            'currently_centered': all(abs(x) <= tolerance for x in error),
            'current_safe_inside_region': inside(safe, r),
            'suggested_translation_px': move, 'translated_safe_bbox': shifted,
            'translated_center_error_px': [error[i]+move[i] for i in range(2)],
            'translated_safe_inside_region': inside(shifted, r),
            'translated_safe_inside_canvas': inside(shifted, frame),
            'visual_inspection_complete': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--canvas', nargs=2, type=float, required=True)
    p.add_argument('--bbox', nargs=4, type=float, required=True)
    p.add_argument('--region', nargs=4, type=float)
    p.add_argument('--safe-bbox', nargs=4, type=float)
    p.add_argument('--tolerance', type=float, default=1)
    a = p.parse_args()
    try:
        print(json.dumps(check(a.canvas, a.bbox, a.region, a.safe_bbox, a.tolerance),
                         ensure_ascii=False, indent=2, allow_nan=False))
    except ValueError as e:
        p.error(str(e))


if __name__ == '__main__':
    main()
