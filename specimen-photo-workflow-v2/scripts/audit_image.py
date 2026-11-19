"""Read-only image invariants. Requires Pillow and NumPy; never edits input images."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    with Image.open(path) as im:
        im.load()
        return np.array(im.convert('RGBA')), {"size": list(im.size), "mode": im.mode,
            "dpi": list(im.info['dpi']) if 'dpi' in im.info else None,
            "icc_sha256": hashlib.sha256(im.info.get('icc_profile', b'')).hexdigest()
                if im.info.get('icc_profile') else None}


def audit(source, output, expected_source_sha256=None, expect_same_size=False,
          protect=(), preserve_black=False, expect_identical=False, mask=None,
          clipping_increase_threshold=0.01, expect_metadata=False, preserve_alpha=False,
          background_only_black=False):
    if not np.isfinite(clipping_increase_threshold) or not 0 <= clipping_increase_threshold <= 1:
        raise ValueError('clipping threshold must be finite and between zero and one')
    a, ai = load(source)
    b, bi = load(output)
    same = a.shape == b.shape
    checks, warnings = {}, []
    source_hash, output_hash = sha256(source), sha256(output)
    if expected_source_sha256 is not None:
        if len(expected_source_sha256) != 64 or any(c not in '0123456789abcdef' for c in expected_source_sha256.lower()):
            raise ValueError('expected hash must contain 64 hexadecimal characters')
        checks['source_hash_unchanged'] = source_hash == expected_source_sha256.lower()
    if expect_same_size:
        checks['same_pixel_dimensions'] = same
    if expect_metadata:
        for field in ['dpi', 'icc_sha256']:
            if ai[field] is not None:
                checks[field+'_preserved'] = bi[field] == ai[field]
    if expect_identical:
        checks['rgba_pixels_identical'] = same and bool(np.array_equal(a, b))
    if preserve_alpha:
        checks['alpha_preserved'] = same and bool(np.array_equal(a[:,:,3], b[:,:,3]))
    h, w = a.shape[:2]
    mask_pixels = None
    if mask is not None:
        with Image.open(mask) as m:
            if m.mode != 'L' or m.size != (w,h):
                raise ValueError('mask must be a same-size L-mode grayscale image')
            mask_pixels = np.array(m)
    if background_only_black and mask_pixels is None:
        raise ValueError('background-only black check requires an independently verified specimen mask')
    excluded = np.zeros((h, w), dtype=bool)
    protected = []
    for rect in protect:
        if len(rect) != 4 or any(type(v) is not int for v in rect):
            raise ValueError('protection rectangle requires four integer pixel coordinates')
        l, t, r, bottom = rect
        if not (0 <= l < r <= w and 0 <= t < bottom <= h):
            raise ValueError('protection rectangle must lie inside source canvas')
        excluded[t:bottom, l:r] = True
        equal = same and bool(np.array_equal(a[t:bottom,l:r], b[t:bottom,l:r]))
        protected.append({"rect": list(rect), "identical": equal})
    if protected:
        checks['protected_regions_identical'] = all(x['identical'] for x in protected)
    black = (a[:,:,:3] == 0).all(axis=2) & (a[:,:,3] == 255)
    if background_only_black:
        black &= mask_pixels == 0
    black_count = int(black.sum())
    if preserve_black:
        if not black_count:
            warnings.append('No opaque pure-black source pixels; black preservation not established')
        else:
            checks['opaque_black_preserved'] = same and bool(np.array_equal(a[black], b[black]))
    roi = (a[:,:,3] > 0) & (a[:,:,:3] != 0).any(axis=2) & ~excluded
    roi_method = 'visible_nonblack_candidate_excluding_protected_regions'
    if mask is not None:
        roi = (mask_pixels > 0) & (a[:,:,3] > 0) & ~excluded
        roi_method = 'caller_supplied_mask_excluding_protected_regions'
    metrics = {"roi_method": roi_method, "roi_pixel_count": int(roi.sum()),
               "source_opaque_black_count": black_count,
               "black_check_scope": 'outside_independent_specimen_mask' if background_only_black else 'all_source_opaque_black'}
    if same and roi.any():
        for name, arr in [('before', a), ('after', b)]:
            rgb = arr[:,:,:3][roi]
            y = rgb.astype(float) @ np.array([0.2126,0.7152,0.0722])
            metrics[name] = {"encoded_y_p70": float(np.percentile(y,70)),
                "any_channel_255_fraction": float((rgb == 255).any(axis=1).mean()),
                "any_channel_zero_fraction": float((rgb == 0).any(axis=1).mean())}
        for field in ['any_channel_255_fraction','any_channel_zero_fraction']:
            delta=metrics['after'][field]-metrics['before'][field]
            metrics[field+'_increase']=delta
            if delta > clipping_increase_threshold:
                warnings.append(field+' increased; inspect detail, not proof of clipping damage')
    else:
        warnings.append('Paired ROI statistics unavailable: changed dimensions or empty ROI')
    if (b[:,:,3] < 255).any():
        visible = b[:,:,3] > 0
        touch = bool(visible[0,:].any() or visible[-1,:].any() or visible[:,0].any() or visible[:,-1].any())
        metrics['alpha_foreground_touches_canvas'] = touch
        if touch:
            warnings.append('Nonzero alpha touches canvas; review intended framing')
    status = 'fail' if any(v is False for v in checks.values()) else 'needs_review' if warnings or not checks else 'pass'
    return {"status": status, "source": {"path": str(source), "sha256": source_hash, **ai},
        "output": {"path": str(output), "sha256": output_hash, **bi},
        "checks": checks, "protected_regions": protected, "metrics": metrics,
        "warnings": warnings, "not_verified": ['tissue_completeness','mask_semantic_accuracy',
            'physical_scale','reference_validity','visual_inspection'],
        "source_snapshot_provided": expected_source_sha256 is not None,
        "clipping_increase_threshold": clipping_increase_threshold}


def rectangle(value):
    try:
        r = [int(x) for x in value.split(',')]
        if len(r) != 4:
            raise ValueError()
        return r
    except ValueError:
        raise argparse.ArgumentTypeError('Use integer left,top,right,bottom') from None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-source-sha256')
    p.add_argument('--expect-same-size', action='store_true')
    p.add_argument('--protect', type=rectangle, action='append', default=[])
    p.add_argument('--preserve-black', action='store_true')
    p.add_argument('--expect-identical', action='store_true')
    p.add_argument('--expect-metadata', action='store_true')
    p.add_argument('--preserve-alpha', action='store_true')
    p.add_argument('--background-only-black', action='store_true')
    p.add_argument('--mask', type=Path)
    p.add_argument('--clipping-increase-threshold', type=float, default=0.01)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    try:
        result = audit(args.source,args.output,args.expected_source_sha256,args.expect_same_size,
            args.protect,args.preserve_black,args.expect_identical,args.mask,args.clipping_increase_threshold,args.expect_metadata,args.preserve_alpha,args.background_only_black)
        text = json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if args.report:
            with args.report.open('x',encoding='utf-8') as f:
                f.write(text)
        print(text,end='')
        return 1 if result['status'] == 'fail' else 3 if result['status'] == 'needs_review' else 0
    except (OSError, ValueError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
