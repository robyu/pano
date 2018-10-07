import logging
import logging.handlers
import sys

"""
example of logging as applied to imported modules

you can run this code via python testlogger.py
or you can use it as a class like this:

        import testlogger
        tester = testlogger.TestLogger()
        tester.test()

"""

class TestLogger:
    logger = None

    def __init__(self):
    """
    create a logger named __name__ (which depends on how this code is executed).

    Assume that the root logger will specify the formatting, loglevel, etc.
    The root logger is configured in the calling code
    
    """    
        self.logger = logging.getLogger(__name__)

        self.logger.debug("init debug")
        self.logger.warning("init warning")
        self.logger.error("init error")
        self.logger.critical("init critical")

    def test(self):
        self.logger.debug("test debug")
        self.logger.warning("test warning")
        self.logger.error("test error")
        self.logger.critical("test critical")

if __name__=="__main__":
    #
    # configure root logger
    logger = logging.getLogger()  # ROOT logger
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    handler.setFormatter(formatter)        
    logger.addHandler(handler)

    logging.warning("execute main")
    tester = TestLogger()
    tester.test()
    
