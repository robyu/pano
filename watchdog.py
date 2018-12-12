#!/usr/bin/env python3
import os
import time
import pudb
import panoconfig
import click
import subprocess
import logging
import logging.handlers
import sys
"""
./watchdog.py --logfname=stdout  --loglevel=debug testdata2/test_pano_b1_only.json
"""
class Watchdog:
    logger = None
    wd_dict = {}
    
    def __init__(self, config, loglevel, logfname):
        self.logger = self.configure_logging(loglevel,logfname)
        self.wd_dict = panoconfig.get_param_dict(config)
        
    def wd_sleep(self, interval_min):
        assert interval_min > 0.0
        interval_sec = 60.0 * interval_min
        time.sleep(interval_sec)
        return

    def get_process_list(self):
        cmd = "ps -ef"   # NOT a list
        try:
            out = subprocess.getoutput(cmd)   # dont use check_output(): returns undesirable byte string
        except subprocess.CalledProcessError:
            out = ""
        #end

        # output of check_output is a single large string,
        # so cut it up at newlines
        out = out.splitlines()
        return out

    def check_ftp_server(self,enable_flag):
        """
        pure-ftpd (IDLE)
        subprocess.check_output(args, *, stdin=None, stderr=None, shell=False, universal_newlines=False
        
        
        $ ps -ef | grep ftpd
        root      6095  6092  0 10:13 pts/0    00:00:00 grep pure-ftpd
        ftpuser  31662   728  0 01:30 ?        00:00:36 pure-ftpd (IDLE)
        root     31663 31662  0 01:30 ?        00:00:00 pure-ftpd (PRIV)
        """
        self.logger.debug("check_ftp_server: enable_flag=%d" % int(enable_flag))
        if (enable_flag==0) or (enable_flag==False):
            return True
        #end
    
        retval = False
        out = self.get_process_list()
        linecount = 0
        for line in out:
            if line.find('ftpd') > 0:
                self.logger.debug(line)
                linecount += 1
            #end
        #end
            
        if linecount >= 2:
            retval = True
        #end

        self.logger.info("check_ftp_server: %s" % str(retval))
        return retval

    def check_breadcrumb(self,enable_flag):
        """
        os.path.join()
        os.path.exists()
        os.remove()
        """
        self.logger.debug("check_breadcrumb: enable_flag=%d" % int(enable_flag))
        if (enable_flag==0) or (enable_flag==False):
            return True

        retval = False
        breadcrumb_fname = 'pano-breadcrumb.txt'

        if os.path.exists('pano-breadcrumb.txt'):
            self.logger.debug("found breadcrumb %s" % breadcrumb_fname)
            retval = True
            os.remove(breadcrumb_fname)
    
        self.logger.info("check_breadcrumb: %s" % str(retval))
        return retval

    def check_http_server(self, enable_flag):
        """
        /usr/sbin/lighttpd -D -f /etc/lighttpd/lighttpd.conf
        """
        self.logger.debug("check_http_server: enable_flag=%d" % int(enable_flag))
        if (enable_flag==0) or (enable_flag==False):
            return True

        retval = False
        out = self.get_process_list()
        linecount = 0
        for line in out:
            #self.logger.debug(line)
            if line.find('httpd') > 0:
                self.logger.debug(line)
                self.logger.debug("found match")
                linecount += 1

        if linecount >= 1:
            retval = True
        
        self.logger.info("check_http_server: %s" % str(retval))
        return retval

    def configure_logging(self, loglevel,logfname):
        """
        see https://docs.python.org/2/howto/logging.html
        
        but see also
        https://stackoverflow.com/questions/20240464/python-logging-file-is-not-working-when-using-logging-basicconfig
        """
        logger = logging.getLogger()

        #
        # normalize loglevel arg
        #
        # assuming loglevel is bound to the string value obtained from the
        # command line argument. Convert to upper case to allow the user to
        # specify --log=DEBUG or --log=debug
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        if logfname=='stdout':
            print("logging to stdout")
            handler = logging.StreamHandler(sys.stdout)
        else:
            print("logging to %s" % logfname)
            handler = logging.handlers.RotatingFileHandler(logfname, maxBytes=4096, backupCount=4)
        #end
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
        handler.setFormatter(formatter)        
        logger.addHandler(handler)

        # because of how logging is imported,    
        # can't set level of root logger using basicConfig
        # see stackoverflow question above
        logger.setLevel(numeric_level)


        logger.debug("test debug")
        logger.info("test info")
        logger.warning("test warning")
        logger.error("test error")
        logger.critical("test critical")

        return logger


    def watch(self):
        num_faults = 0
        max_faults = self.wd_dict['watchdog_max_faults']
        
        sleep_interval_min = self.wd_dict['sleep_interval_min']
        self.logger.info("sleep_interval_min=%d" % sleep_interval_min)
        
        loop_flag = True
        while loop_flag:
            self.logger.info("-----------------")
            self.logger.info("watchdog sleeping: %6.2f min ( %d faults)" % (sleep_interval_min, num_faults))
            self.wd_sleep(sleep_interval_min)
            
            # I originally implemented this with bool logic, but
            # python bools short-circuit, so as soon as one check failed,
            # none of the other checks were executed.  Did not want that.
            miss_count = 0
            miss_count += int(self.check_http_server(self.wd_dict['watchdog_check_httpd'])  ==False)
            miss_count += int(self.check_ftp_server( self.wd_dict['watchdog_check_ftpd'])   ==False)
            miss_count += int(self.check_breadcrumb( self.wd_dict['watchdog_check_breadcrumb']) ==False)
            
            if miss_count > 0:
                num_faults+=1
            else:
                num_faults = 0

            if num_faults >= max_faults:
                loop_flag=False
            #end
        
        #while

        self.logger.critical("# faults (=%d) >= max (=%d)" % (num_faults, max_faults))
        self.logger.critical("exiting watchdog")
        if self.wd_dict['watchdog_enable_reboot']==1:
            self.logger.critical('rebooting')
            os.system('reboot')
        #end
        
        
@click.command()
@click.argument('config')
@click.option('--loglevel',default='info',help='valid values: \'debug\'|\'info\'|\'warning\'|\'error\'|\'critical\'')
@click.option('--logfname',default='watchdog.log',help='specify \'stdout\' for sys.stdout')
def wd_main(config,loglevel,logfname):
    mywd = Watchdog(config, loglevel, logfname)
    mywd.watch()

if __name__=="__main__":
     wd_main()
    
    
