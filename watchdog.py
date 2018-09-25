#!/usr/bin/env python
import os
import time
import pudb
import panoconfig
import click
import subprocess

"""
"""
def wd_sleep(interval_min):
    assert interval_min > 0.0
    interval_sec = 60.0 * interval_min
    time.sleep(interval_sec)
    return

def get_process_list():
    cmd = ['ps','-ef']
    try:
        out = subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        out = ""

    # output of check_output is a single large string,
    # so cut it up at newlines
    out = out.splitlines()

    return out

def check_ftp_server(enable_flag):
    """
    pure-ftpd (IDLE)
    subprocess.check_output(args, *, stdin=None, stderr=None, shell=False, universal_newlines=False

    
    $ ps -ef | grep ftpd
    root      6095  6092  0 10:13 pts/0    00:00:00 grep pure-ftpd
    ftpuser  31662   728  0 01:30 ?        00:00:36 pure-ftpd (IDLE)
    root     31663 31662  0 01:30 ?        00:00:00 pure-ftpd (PRIV)
    """
    if (enable_flag==0) or (enable_flag==False):
        return True
    
    retval = False
    out = get_process_list()
    linecount = 0
    for line in out:
        if line.find('ftpd') > 0:
            linecount += 1

    if linecount >= 2:
        retval = True
        
    return retval

def check_breadcrumb(enable_flag):
    """
    os.path.join()
    os.path.exists()
    os.remove()
    """
    if (enable_flag==0) or (enable_flag==False):
        return True

    retval = False
    breadcrumb_fname = 'pano-breadcrumb.txt'

    if os.path.exists('pano-breadcrumb.txt'):
        retval = True
        os.remove(breadcrumb_fname)
    
    return retval

def check_http_server(enable_flag):
    """
    /usr/sbin/lighttpd -D -f /etc/lighttpd/lighttpd.conf
    """
    if (enable_flag==0) or (enable_flag==False):
        return True

    retval = False
    out = get_process_list()
    linecount = 0
    for line in out:
        if line.find('httpd') > 0:
            linecount += 1

    if linecount >= 2:
        retval = True
        
    return retval

@click.command()
@click.argument('config')
def wd_main(config):
    print("config file=%s" % config)
    wd_dict = panoconfig.get_param_dict(config)
    num_faults = 0
    max_faults = wd_dict['watchdog_max_faults']
    sleep_interval_min = wd_dict['sleep_interval_min']

    loop_flag = True
    while loop_flag:
        print("watchdog sleeping: %6.2f min ( %d faults)" % (sleep_interval_min, num_faults))
        wd_sleep(sleep_interval_min)
        
        miss_flag = False
        miss_flag = miss_flag or (check_http_server(wd_dict['watchdog_check_httpd'])  ==False)
        miss_flag = miss_flag or (check_ftp_server( wd_dict['watchdog_check_ftpd'])   ==False)
        miss_flag = miss_flag or (check_breadcrumb( wd_dict['watchdog_check_breadcrumb']) ==False)

        if miss_flag == True:
            num_faults+=1
        else:
            num_faults = 0

        if num_faults >= max_faults:
            loop_flag=False
        #end
        
    #while

    print("# faults (=%d) >= max (=%d)" % (num_faults, max_faults))
    if wd_dict['watchdog_enable_reboot']==1:
        os.shell('reboot')
    #end

if __name__=="__main__":
    wd_main()
    
    
