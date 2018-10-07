import time
import logging

"""
a decorator for timing code execution

see https://medium.com/pythonhive/python-decorator-to-measure-the-execution-time-of-methods-fa04cb6bb36d
"""
logger = logging.getLogger(__name__)
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            logger.info('\n executed (%r) in  %8.3f s' % \
                        (method.__name__, (te - ts)))
        return result
    return timed


if __name__=="__main__":
    @timeit
    def foo():
        time.sleep(5)
        return 1

    foo()
    
