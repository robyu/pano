

import os
import time
import subprocess
import datastore

def parse_info_amcrest_jpg(row, dir_element_list, fname):
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'jpg', '10', '35']
    # 31[M][0@0][0].jpg
    assert dir_element_list[4]=='jpg'

    row.d['mediatype'] = dir_element_list[4]
    row.d['cam_name'] = dir_element_list[0]

    date = dir_element_list[2]
    hour = int(dir_element_list[5])
    minute = int(dir_element_list[6])
    sec = int(fname[0:2])
    row.d['ctime'] = '%sT%02d:%02d:%02d' % (date, hour, minute, sec)
    return row

def parse_info_amcrest_dav(row, dir_element_list, fname):
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'dav', '11']
    # 11.50.41-11.52.11[M][0@0][0].dav
    assert dir_element_list[4]=='dav'

    row.d['mediatype'] = dir_element_list[4]
    row.d['cam_name'] = dir_element_list[0]
    date = dir_element_list[2]
    hour = int(fname[0:2])
    minute = int(fname[3:5])
    sec = int(fname[6:8])
    row.d['ctime'] = '%sT%02d:%02d:%02d' % (date, hour, minute, sec)
    return row

def parse_info_amcrest(root_dir, dir_path, fname):
    """
    given dir_path, fname,

    e.g.
    root_dir = './temp/FTP'
    dir_path = ./testdata/FTP/b1/AMC002A3_K2G7HH/2018-02-25/001/jpg/18/53
    fname = 29[M][0@0][0].jpg

    return dict:
    {'camera_name':name of camera, 
     'ctime':'yyyy-mm-ddThh:mm:ss.ssss',
    }
    """
    if dir_path.find(root_dir) != 0:
        assert False, "dir_path does not begin with root_dir"

    # chop off root_dir from dir_path
    len_root_dir = len(root_dir)
    dir_path = dir_path[len_root_dir+1:len(dir_path)]   # chop off './temp/FTP/'
    dir_element_list = dir_path.split('/')

    
    # at this point, dir_element_list contains:
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'jpg', '10', '35']
    # or
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'dav', '11']
    print(dir_element_list)
    if len(dir_element_list) < 6:
        return None

    row = datastore.Row()
    row.d['path'] = os.path.join(root_dir, dir_path)
    row.d['fname'] = fname
    print("%s %s" % (row.d['path'], row.d['fname']))
    if dir_element_list[4]=='jpg' and fname[-3:len(fname)]=='jpg':
        row = parse_info_amcrest_jpg(row, dir_element_list, fname)
    elif dir_element_list[4]=='dav' and fname[-3:len(fname)]=='dav':
        row = parse_info_amcrest_dav(row, dir_element_list, fname)
    else:
        print('dont know how to handle %s %s',row.d['path'], row.d['fname'])
        return None
    return row
    
def cull_files_by_ext(root_dir='.', ext_list=['.avi','.idx']):
    num_deleted = 0
    for dir_path, subdir_list, file_list in os.walk(root_dir):
        for fname in file_list:
            full_fname = os.path.join(dir_path, fname)
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
    for dir_path, subdir_list, file_list in os.walk(root_dir):
        for fname in file_list:
            full_fname = os.path.join(dir_path, fname)
            filetime_epoch = os.path.getmtime(full_fname)
            localtime = time.localtime(filetime_epoch)
            # print("%s/%s mtime=%s" % (dir_path, fname, time.asctime(localtime)))
            diff_sec = baseline_time_epoch - filetime_epoch
            if diff_sec > cull_threshold_sec:
                print("delete %s (mtime = %s, %f sec > %f sec)" % (fname, time.asctime(localtime), diff_sec, cull_threshold_sec))
                try:
                    os.remove(full_fname)
                    num_deleted += 1
                except OSError:
                    pass
    return num_deleted

def cull_empty_dirs(root_dir):
    """
    execute: 
    find root_dir -type d -empty -exec rm {} ;

    returns:
    none
    """
    subprocess.call(['pwd'])
    subprocess.call(['which','find'])
    subprocess.call(['ls',root_dir])
    # print empty dirs
    subprocess.call(['find',root_dir,'-type','d','-empty','-print'])
    print(['find',root_dir,'-type','d','-empty','-print'])

    # delete empty dirs
    subprocess.call(['find',root_dir,'-type','d','-empty','-exec','rm','-rf','{}',';'])


def walk_dir_and_load_db(db, root_dir='.'):
    #
    # first cull dirs
    cull_empty_dirs(root_dir)
    
    for dir_path, subdir_list, file_list in os.walk(root_dir):
        for fname in file_list:
            # TODO: get mtime
            row = parse_info_amcrest(root_dir, dir_path, fname)
            if (row != None):
                db.add_row(row)
        #end
    #end
    db.dbconn.commit()
    

if __name__=="__main__":
    baseline_time = time.strptime("26 feb 2018 00:00", "%d %b %Y %H:%M")
    baseline_time_epoch = time.mktime(baseline_time)
    num_deleted = cull_files(baseline_time_epoch=baseline_time_epoch, cull_threshold_days=1)
    print(num_deleted)
