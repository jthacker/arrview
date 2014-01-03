import numpy as np
from numpy.testing import assert_array_equal

from .. import colormapper as cm

class TestColorMapper(object):
    def test_conversion_invariance(self):
        h,w = 2,4 # Product cannot be > 255
        x = np.arange(h*w).reshape(h,w)
       
        # Replicates array for each color channel
        def cm_ident(a):
            return np.dstack((a,a,a))
             
        arr = cm.pixdata_to_ndarray(cm.ndarray_to_pixdata(x, cmap=cm_ident, norm=lambda x: x/255.0),h,w)
        assert_array_equal(x, arr[:,:,0]) 
        assert_array_equal(x, arr[:,:,1]) 
        assert_array_equal(x, arr[:,:,2]) 
