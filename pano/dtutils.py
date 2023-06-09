import datetime as dt

"""
date-time utils
"""

def sec_to_str(time_sec, fmt="%Y-%m-%d %H:%M:%S"):
    """
    convert unix epoch seconds to custom format in local time

    see https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
    for formatting
    """
    t = dt.datetime.fromtimestamp(float(time_sec))
    #time_str = t.strftime(fmt) + " %s" % str(time_sec)
    time_str = t.strftime(fmt) 
    return time_str
    
def now_to_str(fmt="%Y-%m-%d %H:%M"):
    """
    see https://www.saltycrane.com/blog/2008/06/how-to-get-current-date-and-time-in/
    """
    now = dt.datetime.now()
    time_str = now.strftime(fmt)
    return time_str
