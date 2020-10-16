# Need clever way to filter the peaks
# Center should be within a known box, peaks should be symmetric on either side at equal distances
# but depends on the grating and center
import numpy as np
import lsst.geom

import logging
logger = logging.getLogger('findNarrowbandRonchiPeak_logger')


def findNarrowbandRonchiPeaks(sources, center_bbox, wavelength, dispersion, spectral_position_angle):

    #  dispersion in pixels/nm
    # wavelength in nm
    
    # Verify inputs
    if (spectral_position_angle < 0.0) | (spectral_position_angle > 90.0):
        return(ValueError('Given spectral_position_angle {} must be between 0 and 90 degrees'.format()))
    
    # find the center peak by checking for peaks in center_bbox
    # This needs proper error handling
    try:
        center_source, center_peak = findBrightestSourceInBox(sources, center_bbox)
    except OSerror:
        print('No zeroth order peak found in bounding box!')
        
    
    logger.info('Zeroth order peak is at {}, {}'.format(center_peak.getIx(), center_peak.getIy()))
    
    # guess position of peak from dispersion and position angle
    # then create bounding boxes for the objects

    if dispersion != None:
        logger.info('Searching for +/1 orders with dispersion = {} [pixels/nm]'.format(dispersion))
        first_ord_dist = wavelength*dispersion

        peak1_guess = lsst.geom.Point2D(center_peak.getIx() + first_ord_dist * np.sin(spectral_position_angle), 
                                  center_peak.getIy() + first_ord_dist * np.cos(spectral_position_angle))
        peak1_bbox = lsst.geom.Box2I.makeCenteredBox(peak1_guess, center_bbox.getDimensions()) 

        peak2_guess = lsst.geom.Point2D(center_peak.getIx() - first_ord_dist * np.sin(spectral_position_angle), 
                                  center_peak.getIy() - first_ord_dist * np.cos(spectral_position_angle))
        peak2_bbox = lsst.geom.Box2I.makeCenteredBox(peak2_guess, center_bbox.getDimensions()) 

        # Now see if there are actually sources associated inside the bounding boxes
        try:
            logger.debug('Starting to search for order +1 where peak1_bbox is {}'.format(peak1_bbox))
            peak1_source, peak1_peak = findBrightestSourceInBox(sources, peak1_bbox)
            logger.info('Order +1 peak for {:1.2f} nm estimated to be at {}'.format(wavelength, peak1_peak))
        except OSerror:
            print('No order +1 peak found in bounding box!')

        # Now see if there are actually sources associated with these
        try:
            logger.debug('Starting to search for order -1 where peak2_bbox is {}'.format(peak2_bbox))
            peak2_source, peak2_peak = findBrightestSourceInBox(sources, peak2_bbox)
            logger.info('Order -1 peak for {:1.2f} nm estimated to be at {}'.format(wavelength, peak2_peak))
        except OSerror:
            print('No order -1 peak found in bounding box!')

        return(center_source, peak1_source, peak2_source)
    else:
        logger.info('Dispersion set to None, returning only center source')
        return(center_source)

def findBrightestSourceInBox(sources, bbox):
    logger.debug('Starting loop over {} sources in catalogue'.format(len(sources)))
    logger.debug('Searching for sources in {}'.format(bbox))
    identified_source=None
    identified_peak=None
    for s in sources:
        peak=s.getFootprint().getPeaks()[0]
        peak.getF() # gives point2d, need point2i for contains function
        if bbox.contains(lsst.geom.Point2I(peak.getF())):
            logger.debug('Peak {},{} FOUND inside bounding box'.format(peak.getIx(), peak.getIy()))
            # Handle the case of the first source found
            if identified_source == None:
                identified_source = s
                identified_peak = peak
            # Handle the case of multiple sources, taking the brightest
            # This might lead to issues with cosmics
            elif (peak.getPeakValue() > identified_peak.getPeakValue()):
                logger.debug('Replacing peak {},{} with {}, {}'.format(
                    identified_peak.getIx(), identified_peak.getIy(), peak.getIx(), peak.getIy()))
                identified_source = s
                identified_peak = peak
            else:
                logger.debug('Peak {},{} fainter than previously found object in box, ignoring'.format(peak.getIx(), peak.getIy()))
                #    raise OSError('Something went wrong, this should never happen')
        else:
            # This was too annoying but I don't really understand logging levels enough
            # to have multiple debug levels, so commenting it out.
            #logger.debug('Peak {},{} not inside bounding box'.format(peak.getIx(), peak.getIy()))
            continue
    
    if identified_source == None:
        logger.critical('No identified source found in bounding box')
        raise OSError('No identified sources found in supplied bounding box')
    
    return(identified_source, identified_peak)