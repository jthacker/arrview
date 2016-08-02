from collections import defaultdict
import logging

import h5py
import numpy as np
import skimage.draw
import time

from arrview.roi import ROI
from arrview.slicer import SliceTuple


log = logging.getLogger(__name__)

_file_description = 'A collection of ROIs'

_version = 1

# Compress masks using gzip
_compression_type = 'gzip'

# GZIP compression level can be from 0 to 9, 9 is maximum compression
_compression_opts = 4


class ROIFormatError(Exception):
    pass


def store_rois(rois, filename):
    """Save ROIs to filename

    Parameters
    ----------
    rois : iterable
        iterable of ROIs to save
    filename : str
        name of file to save ROIs to
    """
    with h5py.File(filename, 'w') as f:
        f.attrs['version'] = _version
        f.attrs['description'] = _file_description
        f.attrs['creation_time'] = time.time()
        root = f.create_group('rois')
        for i, roi in enumerate(rois):
            roigrp = root.create_group('roi_%d' % i)
            roigrp.attrs['index'] = i
            roigrp.attrs['name'] = roi.name
            roigrp.create_dataset('mask',
                                  data=roi.mask,
                                  dtype=bool,
                                  compression=_compression_type,
                                  compression_opts=_compression_opts)
        log.debug('rois saved to:{!r} count:{!r} version:{!r} time:{!r}'
                .format(filename, len(rois), _version, f.attrs['creation_time']))


def load_rois(filename, shape=None):
    """Load ROIs from filename

    Parameters
    ----------
    filename : str
        name of file to load ROIs from
    shape : (default: None) tuple
        shape of ROI masks, used only for loading version 0 ROI files

    Returns
    -------
    List of ROIs loaded from file
    """
    rois = {}
    with h5py.File(filename, 'r') as f:
        version = f.attrs.get('version')
        log.debug('loading ROIs from {!r}, version: {!r}'.format(filename, version))
        if version == 1:
            return _parse_version1(f)
        return _parse_version0(f, shape)

def _parse_version1(f):
    rois = {}
    creation_time = f.attrs.get('creation_time')
    for roigrp in f['/rois'].itervalues():
        index = roigrp.attrs['index']
        rois[index] = ROI(
                name=roigrp.attrs['name'],
                mask=roigrp['mask'].value)
    return [rois[i] for i in sorted(rois)]


# Used by _parse_version0 for backward comptibility with polygon masks
def _create_mask(shape, slc, poly, collapse=False):
    """Convert a polygon to a binary mask according the specified array shape
    Args:
        shape    -- a tuple with the size of each dimension in the mask
        slc      -- SliceTuple describing where to apply the polygon to
        poly     -- A numpy array of (x,y) point pairs describing a polygon
        collapse -- Ignore any dimensions > the number of dimensions in shape (i.e. len(shape))

    Returns:
        binary mask with the region in poly set to False and everywhere else
        set to True
    """
    mask = np.zeros(shape, dtype=bool)
    if len(poly) > 0:
        viewShape = shape[slc.ydim],shape[slc.xdim]
        y, x = skimage.draw.polygon(y=poly[:,1], x=poly[:,0], shape=viewShape)
        idxs = slc.slice_from_screen_coords(x, y, mask)
        if collapse:
            idxs = idxs[:mask.ndim]
        mask[idxs] = True
    return mask


def _convert_version0(roi_dict, shape):
    rois = []
    for name, _rois in roi_dict.items():
        if _rois:
            roi = ROI(name=name, mask=np.zeros(shape, dtype=bool))
            for _roi in _rois:
                mask = _create_mask(shape, _roi['slc'], _roi['poly'], collapse=True)
                roi.mask = np.logical_or(roi.mask, mask)
            rois.append((_rois[0]['slc'], roi.name, roi))
    return [r[2] for r in sorted(rois, key=lambda r: (r[0], r[1]))]


def _parse_version0(f, shape):
    assert shape, 'shape must be set to parse version 0 ROI files'
    rois = defaultdict(list)
    for roigrp in f['/rois'].itervalues():
        viewdims = roigrp.attrs['viewdims']
        arrslc = roigrp.attrs['arrslc']
        roi = dict(
                name=roigrp.attrs['name'],
                poly=roigrp['poly'].value,
                slc=SliceTuple.from_arrayslice(arrslc, viewdims))
        rois[roi['name']].append(roi)
    return _convert_version0(rois, shape)
