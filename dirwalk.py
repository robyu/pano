

import os
import time
import subprocess


def parse_datetime(root_dir, dir_name, fname):
    """
    given dir_name, fname,

    e.g.
    root_dir = './temp/FTP'
    dir_name = ./testdata/FTP/b1/AMC002A3_K2G7HH/2018-02-25/001/jpg/18/53
    fname = 29[M][0@0][0].jpg

    return dict:
    {'camera_name':nnn, 
    'date':nnn, 
    'time':nnn}
    """
    if dir_name.find(root_dir) != 0:
        assert False, "dir_name does not begin with root_dir"

    # chop off root_dir from dir_name
    len_root_dir = len(root_dir)
    dir_name = dir_name[len_root_dir+1:len(dir_name)]   # chop off './temp/FTP/'
    dir_element_list = dir_name.split('/')

    
    # at this point, dir_element_list contains:
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'jpg', '10', '35']
    # or
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'dav', '11']

    print(dir_element_list)
    if len(dir_element_list) < 6:
        return
    camera_name = dir_element_list[0]
    date = dir_element_list[2]

    if dir_element_list[4]=='jpg':
        hour = dir_element_list[5]
        minute = dir_element_list[6]
        sec = fname[0:2]
    else:
	# 11.50.41-11.52.11[M][0@0][0].dav
        assert dir_element_list[4]=='dav'
        hour = dir_element_list[5]
        fname_element_list = fname.split('.')
        minute = fname_element_list[1]
        sec = fname_element_list[2]
    print("%s:%s:%s" % (hour, minute, sec))
        
        
    
def cull_files_by_ext(root_dir='.', ext_list=['.avi','.idx']):
    num_deleted = 0
    for dir_name, subdir_list, file_list in os.walk(root_dir):
        for fname in file_list:
            full_fname = os.path.join(dir_name, fname)
            (root, ext) = os.path.splitext(fname)  # split foo.bar into 'foo', '.bar'
            if ext in ext_list:
                print("found %s in delete list" % fname)
                try:
                    os.remove(full_fname)
                    num_deleted += 1
                except OSError:
                    pass
    return num_deleted
    

def cull_files_by_age(baseline_time_epoch=None, cull_threshold_days=14, root_dir='.'):
    """
    given:
    baseline_time_epoch = baseline time, specified in epoch seconds, see runtests.py::test_cull_files
    cull_threshold_days = number of days allowed after baseline time
    root_dir = starting directory

    delete files (NOT directories)

    returns:
    number of files deleted 
    """
    num_deleted = 0
    cull_threshold_sec = cull_threshold_days * 24 * 60 * 60
    if baseline_time_epoch==None:
        baseline_time_epoch = time.time()  # current time in epoch seconds
    for dir_name, subdir_list, file_list in os.walk(root_dir):
        for fname in file_list:
            full_fname = os.path.join(dir_name, fname)
            filetime_epoch = os.path.getmtime(full_fname)
            localtime = time.localtime(filetime_epoch)
            # print("%s/%s mtime=%s" % (dir_name, fname, time.asctime(localtime)))
            diff_sec = baseline_time_epoch - filetime_epoch
            if diff_sec > cull_threshold_sec:
                print("delete %s (mtime = %s, %f sec > %f sec)" % (fname, time.asctime(localtime), diff_sec, cull_threshold_sec))
                try:
                    os.remove(full_fname)
                    num_deleted += 1
                except OSError:
                    pass
    return num_deleted

def cull_empty_dir(root_dir):
    """
    execute: 
    find root_dir -type d -empty -exec rm {} ;

    returns:
    none
    """
    # print empty dirs
    subprocess.call(['find',root_dir,'-type','d','-empty','-print'])

    # delete empty dirs
    subprocess.call(['find',root_dir,'-type','d','-empty','-exec','rm','-rf','{}',';'])



if __name__=="__main__":
    baseline_time = time.strptime("26 feb 2018 00:00", "%d %b %Y %H:%M")
    baseline_time_epoch = time.mktime(baseline_time)
    num_deleted = cull_files(baseline_time_epoch=baseline_time_epoch, cull_threshold_days=1)
    print(num_deleted)
