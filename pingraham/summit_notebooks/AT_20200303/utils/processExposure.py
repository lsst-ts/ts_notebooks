def processExposure(exposure, bias=None, defects=None, repair=False, repo=None) :
    from lsst.ip.isr import IsrTask
    import lsst.daf.persistence as dafPersist
    import time

    config = IsrTask.ConfigClass()
    
    if (bias==None or defects ==None) and repo == None:
        raise(AttributeError('Repo keyword not set and is required to find bias/defect frames'))
    else:
        butler = dafPersist.Butler(repo)
    
    if False:
        config.overscanFitType = "AKIMA_SPLINE"
        config.overscanOrder = 5
    else:
        config.overscanFitType = "POLY"
        config.overscanOrder = 3

    config.doBias = False #True
    if config.doBias == True and bias == None:
        bias = butler.get('bias', visit=exposure.getInfo().getVisitInfo().getExposureId(), )
        
    config.doDark = False
    config.doFringe = False
    config.doFlat = False
    config.doLinearize = False
    # TODO: should be able to run this but there are issues with defects in the stack at the moment
    config.doDefect = True if repair == True else False   
    if (config.doDefect == True and bias == None):

        butler = dafPersist.Butler(repo)
        defects = butler.get('defects', visit=exposure.getInfo().getVisitInfo().getExposureId(), )
        
    config.doAddDistortionModel = False
    config.doSaturationInterpolation = False
    config.overscanNumLeadingColumnsToSkip = 20

    isrTask = IsrTask(config=config)
    
    # Run ISR
    start = time.time()
    isr_corrected_exposure = isrTask.run(exposure, bias=bias, defects=defects).exposure
    end = time.time()
    print('Time to perform image ISR was {0:2f} [s]'.format(end - start))
    
    return(isr_corrected_exposure)

