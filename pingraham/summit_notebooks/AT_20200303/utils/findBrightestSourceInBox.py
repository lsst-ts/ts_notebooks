def findBrightestSourceInBox(sources, bbox):
    import numpy as np
    import lsst.geom

    import logging
    logger = logging.getLogger('findBrightestSourceInBox_logger')
    
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
        raise ValueError('No identified sources found in supplied bounding box')
    
    return(identified_source, identified_peak)