import numpy as np
import lsst.geom

import logging
logger = logging.getLogger('calc_CofM_logger')

def calc_CofM(exposure):
    # Function takes an ExposureF in module lsst.afw.image.exposure.exposure object
    
    im=exposure.image.array
    bbox=exposure.getBBox()
    
    # Build 2d index arrays for calculations
    pix_index_1d_arr=np.arange(bbox.getBeginX(), bbox.getEndX(), 1)
    ones_array_2d=np.ones([bbox.getWidth(), bbox.getHeight()])
    x_index_arr_2d=pix_index_1d_arr*ones_array_2d
    
    # Can't use transpose since we're supporting non-symmetrical arrays
    pix_index_1d_arr=np.arange(bbox.getBeginY(), bbox.getEndY(), 1)
    onesarray_2d=np.ones([bbox.getHeight(), bbox.getWidth()])
    # array will be left to right so need to transpose
    y_index_arr_2d=np.transpose(pix_index_1d_arr*ones_array_2d)

    # Calculate the centroid
    x_CofM = np.sum(x_index_arr_2d*im)/np.sum(im)
    y_CofM = np.sum(y_index_arr_2d*im)/np.sum(im)
    
    logger.info('x_CofM is {}'.format(x_CofM))
    logger.info('y_CofM is {}'.format(y_CofM))
    return(x_CofM, y_CofM)