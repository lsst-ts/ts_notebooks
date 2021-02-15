import numpy as np
import matplotlib.pyplot as plt
    
def fit_2d_PSF(exposure, plot=True, model='Gaussian2D'):
    """Gaussian fitting algorithm for LSST Stack exposure objects
    Uses astroPy model fitting of 2D gaussian, but on a stack image.
    Parameters
    ----------
    exposure : ``ExposureF in module lsst.afw.image.exposure.exposure object``
        Exposure object from LSST stack
    plot : `Boolean` (default = True)
        Plots the data, fit and residuals.
    model: `string`
        Model to be used in the fit
        
    Raises
    ------
    Nothing for the moment
    
    Returns
    -------
    fit object, y, x : ``Gaussian2D in module astropy.modeling.functional_models object`` , ndarray object, ndarray object
            Fit object with all parameters, 2d pixel maps in x and y for plotting
    Notes
    -----
    This is an algorithm to quickly fit 2D-gaussians to LSST stack objects.
    This is meant to be used with sub-images/stamps where the star is already
    at the center of the stamp.
    """
  
    import warnings
    from astropy.modeling import models, fitting
    
    # Generate x,y,z data, where z is the 2d data
    z=exposure.image.array
    bbox=exposure.getBBox()
    y, x = np.mgrid[bbox.getBeginY():bbox.getEndY(), bbox.getBeginX():bbox.getEndX()]

    # Fit the data using astropy.modeling
    if model.lower() == 'Gaussian2D'.lower():
        #p_init = models.Gaussian2D(amplitude=np.nanmax(z),x_mean=bbox.getCenterX(), y_mean=bbox.getCenterY(), fixed={'theta':True})
        p_init = models.Gaussian2D(amplitude=np.nanmax(z),x_mean=(bbox.getBeginX()+bbox.getEndX())/2.0, 
                                   y_mean=(bbox.getBeginY()+bbox.getEndY())/2.0, 
                                   x_stddev=1.0,y_stddev=1.0,fixed={'theta':True})
    elif model.lower() == 'Moffat2D'.lower():
        print('Moffat!')
        p_init = models.Moffat2D(amplitude=np.nanmax(z),x_0=(bbox.getBeginX()+bbox.getEndX())/2.0, 
                           y_0=(bbox.getBeginY()+bbox.getEndY())/2.0, 
                           gamma=1.0,alpha=3.0)
    else:
        raise KeyError('Only Moffat2D and Gaussian2D models are supported')
        
    fit_p = fitting.LevMarLSQFitter()

    with warnings.catch_warnings():
        # Ignore model linearity warning from the fitter
        warnings.simplefilter('ignore')
        p = fit_p(p_init, x, y, z)

    # Plot the data with the best-fit model
    if plot == True:
        plt.figure(figsize=(13, 5))
        plt.subplot(1, 3, 1)
        extent=[bbox.getBeginX(),bbox.getEndX(), bbox.getBeginY(),bbox.getEndY()]
        plt.imshow(z, origin='lower', interpolation='nearest', extent=extent)#, vmin=-1e4, vmax=5e4)
        plt.title("Data")
        plt.subplot(1, 3, 2)
        plt.imshow(p(x, y), origin='lower', interpolation='nearest', extent=extent)#, vmin=-1e4, vmax=5e4)
        plt.title("Model")
        plt.subplot(1, 3, 3)
        plt.imshow(z - p(x, y), origin='lower', interpolation='nearest', extent=extent)#, vmin=-1e4, vmax=5e4)
        plt.title("Residual")
        print(repr(p))
            
    return(p, y, x)

