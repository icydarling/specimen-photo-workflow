"""Verify original file hash and unretouched opaque pixels before layout/brightness.

Requires Pillow/NumPy. Use a same-Photoshop-decoder baseline, not a different JPEG decoder.
Does not edit images or certify mask semantics or semi-transparent edge completeness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def verify(source, expected_hash, baseline, isolated):
    if len(expected_hash)!=64 or any(c not in '0123456789abcdef' for c in expected_hash.lower()):
        raise ValueError('Expected source hash must contain 64 hexadecimal characters')
    with Image.open(source) as im:source_size=im.size
    with Image.open(baseline) as im:b=np.array(im.convert('RGB'))
    with Image.open(isolated) as im:a=np.array(im.convert('RGBA'))
    same=b.shape[:2]==a.shape[:2] and tuple(source_size)==(a.shape[1],a.shape[0])
    source_hash=digest(source)
    checks={'original_file_unchanged':source_hash==expected_hash.lower(),'same_source_dimensions':same}
    count=0;different=None
    if same:
        opaque=a[:,:,3]==255;count=int(opaque.sum())
        different=int(np.count_nonzero(np.any(a[:,:,:3][opaque]!=b[opaque],axis=1)))
        checks['opaque_source_rgb_unchanged']=count>0 and different==0
    else:checks['opaque_source_rgb_unchanged']=False
    return {'status':'pass' if all(checks.values()) else 'fail','checks':checks,
        'source':str(source),'source_sha256':source_hash,'decoded_baseline':str(baseline),
        'isolated':str(isolated),'opaque_pixels_compared':count,'different_opaque_pixels':different,
        'not_verified':['baseline_provenance_requires_caller_record','mask_semantics',
            'semi_transparent_edges','tissue_completeness','physical_scale']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--expected-source-sha256',required=True)
    p.add_argument('--decoded-baseline',type=Path,required=True)
    p.add_argument('--isolated',type=Path,required=True)
    p.add_argument('--report',type=Path)
    args=p.parse_args()
    try:
        result=verify(args.source,args.expected_source_sha256,args.decoded_baseline,args.isolated)
        text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if args.report:
            with args.report.open('x',encoding='utf-8') as f:f.write(text)
        print(text,end='')
        return 0 if result['status']=='pass' else 1
    except (OSError,ValueError) as e:p.error(str(e))


if __name__=='__main__':raise SystemExit(main())
