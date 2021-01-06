import numpy as np
import lsst.geom
import matplotlib.pyplot as plt

import logging
logger = logging.getLogger('calc_encirlced_energy_logger')

def calc_encircled_energy(exposure, bin=None, plot=False):

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
    
    # Encircled Energy array definition
    x_arr_2d = x_index_arr_2d - x_CofM
    y_arr_2d = y_index_arr_2d - y_CofM
        
    # create array of radial distances (in pixels)
    r_arr_2d=np.sqrt(x_arr_2d**2 + y_arr_2d**2)

    # Just for diagnostics
    if False:
        plt.imshow(y_arr_2d)
        plt.show()
        plt.close()
    
    r_arr_1d=np.reshape(r_arr_2d, (bbox.getHeight() * bbox.getWidth()))   
    z_values_1d = np.reshape(im, (bbox.getHeight() * bbox.getWidth()))

    # Just for diagnostics
    if False:
        plt.ylabel('Intensity [ADU]')
        plt.plot(r_arr_1d, z_values_1d, '.')
        plt.title('PSF intensity pixels as a fxn of radius')
        plt.xlabel('radius [pixels]')
        plt.show()
        plt.close()
    

    # sort the arrays so they're easier to loop/bin
    ind= np.argsort(r_arr_1d)
    ordered_r_arr_1d = r_arr_1d[ind]
    ordered_z_values_1d = z_values_1d[ind]

    rad_pix_list = [] # is it better to append to lists? or can you append to numpy arrays?
    E_wrt_rad_list = []
    EE_arr_list = []
    total_flux = sum(ordered_z_values_1d)
    rad=0 # declare starting place.
    dx0=0.5 # declare starting bin size for every bin
    dx=dx0 # declare starting bin size for first try
    while rad < np.nanmax(ordered_r_arr_1d):
        # Find values inside the bin
        ind1 = ordered_r_arr_1d < (rad+dx)
        ind2 = ordered_r_arr_1d > (rad)
        good = ind1*ind2
        if sum(good) > 0:
            rad_pix_list.append(rad+dx/2) # center of the bin
            E_wrt_rad_list.append(sum(ordered_z_values_1d[good])/total_flux)
            EE_arr_list.append(sum(E_wrt_rad_list))

            dx=dx0
            rad+=dx
        else:
            dx+=1
        #print('rad and dx are {}, {}'.format(rad,dx))

    if plot == True:
        plt.figure(figsize=(13, 5))
        plt.ylabel('Fraction of Encircled Energy')
        plt.plot(np.array(rad_pix_list), EE_arr_list, '.')
        plt.title('Encircled Energy')
        plt.xlabel('radius [pixels]')
        plt.show()
        plt.close()
    
    # Get the values at radii of 50, 67 and 80%
    EE_rad50_pix, EE_rad67_pix, EE_rad80_pix = np.interp([0.50, 0.67, 0.80], np.array(EE_arr_list), np.array(rad_pix_list))
    logger.info('EE radius at 50%, 67% and 80% is [{:0.3f}, {:0.3f}, {:0.3f}] pixels'.format(EE_rad50_pix, EE_rad67_pix, EE_rad80_pix))

    return(EE_rad50_pix, EE_rad67_pix, EE_rad80_pix)
