async def grabATImage(visitID, repo, timeout=20, poll_freq_hz = 1):

    # This grabs an image from the butler but polls for the ingest
    
    # timeout is how long (in seconds) to try before raising an exception
    
    # Poll frequency is how fast to poll for new images (Hz)
    import time
    import lsst.daf.persistence as dafPersist
    import asyncio
    

    sleep_time= 1.0 / poll_freq_hz # frequency in Hz
    exposure = None

    attempt=0
    time_elapsed=0
    start = time.time()

    while (time_elapsed < timeout):
        # have to read in the data each time
        butler = dafPersist.Butler(repo)
        
        try:
    #        exposure = butler.get('raw', visit='234234234')
            exposure = butler.get('raw', visit=visitID)
            
            end = time.time()
            time_elapsed = end-start
            print('Exposure retrieved after waiting {0:0.2f} [s]'.format(time_elapsed))
            return(exposure)
        #except NoResults as noresults:
        except:
            end = time.time()
            time_elapsed = end-start
            print('Image not yet in butler repo. Attempt #{0}, time_elapsed {1:0.2f} [s]'.format(attempt, time_elapsed))
            await asyncio.sleep(sleep_time)
            attempt+=1


    else:
        raise NameError('No image found in the timeout of {} [s]'.format(timeout))
    
    return(exposure)

