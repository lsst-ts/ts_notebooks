import sys
import time
import logging
from threading import Thread

import SALPY_Test


t0 = time.time()
t1 = time.time()

# list of info about one subscription option:
# * subscription command name
# * command that returns all topic names for this kind of subscription
# * prefix for full name of topic
info_list = (
    ("salCommand", "getCommandNames", "Test_command_"),
    ("salProcessor", "getCommandNames", "Test_command_"),
    ("salEventPub", "getEventNames", "Test_logevent_"),
    ("salEventSub", "getEventNames", "Test_logevent_"),
    ("salTelemetrySub", "getTelemetryNames", "Test_"),
    ("salTelemetryPub", "getTelemetryNames", "Test_"),
)

def timeit(sub, name, topic):
    log = logging.getLogger(f"{name}_{topic}")
    log.debug("Starting...")
    time.sleep(1.)
    start_time = time.time()
    sub(topic)
    end_time = time.time()
    log.info(f":: {end_time - start_time}")
    log.debug("Endg...")
    
def time_subscribe(what_list):
    """Subscribe to topics and time it

    Parameters
    ----------
    what_list : `list` of `int`
        What to subscribe to, in order. Each element is one of:

        * 0: salCommand
        * 1: salProcessor
        * 2: salEventPub
        * 3: salEventSub
        * 4: salTelemetryPub
        * 5: salTelemetrySub
    """
    manager = SALPY_Test.SAL_Test(1)

    blocking_tasks = []
    for what in what_list:
        subscribename, getnamesname, prefix = info_list[what]
        subscribefunc = getattr(manager, subscribename)
        getnamesfunc = getattr(manager, getnamesname)
        topics = [prefix + name for name in getnamesfunc()]
        for topic in topics:
#             blocking_tasks.append(loop.run_in_executor(executor, timeit, subscribefunc, subscribename, topic))
            t = Thread(target=timeit, args=(subscribefunc, subscribename, topic))
            t.start()
            blocking_tasks.append(t)
        
        for t in blocking_tasks:
            t.join()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(threadName)010s %(name)018s: %(message)s'
    )    
    start_time = time.time()
    time_subscribe(range(6))
    end_time = time.time()
    print(end_time - start_time)
