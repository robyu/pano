#!/usr/bin/env python
import os
import time
import pudb
import panoconfig
import click
"""
"""
def wd_sleep(interval_min):
    assert interval_min > 0.0
    interval_sec = 60.0 * interval_min
    time.sleep(interval_sec)
    return
    
def check_ftp_server():
    return True

def check_breadcrumb():
    return True

def check_http_server():
    return True

@click.command()
@click.argument('config')
def wd_main(config):
    print("config file=%s" % config)
    wd_dict = panoconfig.get_param_dict(config)
    num_faults = 0
    max_faults = wd_dict['watchdog_max_faults']
    sleep_interval_min = wd_dict['watchdog_interval_min']

    loop_flag = True
    while loop_flag:
        print("watchdog sleeping: %6.2f min ( %d faults)" % (sleep_interval_min, num_faults))
        wd_sleep(sleep_interval_min)
        
        miss_flag = False
        miss_flag = miss_flag or (check_http_server()  ==False)
        miss_flag = miss_flag or (check_ftp_server()   ==False)
        miss_flag = miss_flag or (check_breadcrumb()   ==False)

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
    
    
