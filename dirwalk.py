
import os
import time
import subprocess
import datastore
import derived

def parse_info_amcrest_jpg(row, dir_element_list, fname):
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'jpg', '10', '35']
    # 31[M][0@0][0].jpg
    assert dir_element_list[4]=='jpg'

    row.d['mediatype'] = datastore.MEDIA_IMAGE
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

    row.d['mediatype'] = datastore.MEDIA_VIDEO
    row.d['cam_name'] = dir_element_list[0]
    date = dir_element_list[2]
    hour = int(fname[0:2])
    minute = int(fname[3:5])
    sec = int(fname[6:8])
    row.d['ctime'] = '%sT%02d:%02d:%02d' % (date, hour, minute, sec)
    return row

def parse_info_amcrest(base_data_dir, dir_path, fname):
    """
    given dir_path, fname,

    e.g.
    base_data_dir = './temp/FTP'
    dir_path = ./testdata/FTP/b1/AMC002A3_K2G7HH/2018-02-25/001/jpg/18/53
    fname = 29[M][0@0][0].jpg

    return dict:
    {'camera_name':name of camera, 
     'ctime':'yyyy-mm-ddThh:mm:ss.ssss',
    }
    """
    if dir_path.find(base_data_dir) != 0:
        assert False, "dir_path does not begin with base_data_dir"

    # chop off base_data_dir from dir_path
    len_base_data_dir = len(base_data_dir)
    dir_path = dir_path[len_base_data_dir+1:len(dir_path)]   # chop off './temp/FTP/'
    dir_element_list = dir_path.split('/')

    
    # at this point, dir_element_list contains:
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'jpg', '10', '35']
    # or
    # ['b0', 'AMC0028V_795UUB', '2018-02-24', '001', 'dav', '11']
    if len(dir_element_list) < 6:
        return None

    row = datastore.Row()
    row.d['path'] = dir_path
    row.d['fname'] = fname
    row.d['base_data_dir'] = base_data_dir
    if dir_element_list[4]=='jpg' and fname[-3:len(fname)]=='jpg':
        row = parse_info_amcrest_jpg(row, dir_element_list, fname)
    elif dir_element_list[4]=='dav' and fname[-3:len(fname)]=='dav':
        row = parse_info_amcrest_dav(row, dir_element_list, fname)
    else:
        #print('dont know how to handle %s %s' % (row.d['path'], row.d['fname']))
        return None
    return row
    
def cull_files_by_ext(base_data_dir='.', ext_list=['.avi','.idx']):
    num_deleted = 0
    for dir_path, subdir_list, file_list in os.walk(base_data_dir):
        for fname in file_list:
            full_fname = os.path.join(dir_path, fname)
            (root, ext) = os.path.splitext(fname)  # split foo.bar into 'foo', '.bar'
            if ext in ext_list:
                #print("found %s in delete list" % fname)
                try:
                    os.remove(full_fname)
                    num_deleted += 1
                except OSError:
                    pass
    return num_deleted
    

def cull_files_by_age(db, baseline_time=None, derived_dir=derived.DERIVED_DIR,max_age_days=14):
    """
    given file entries in db,
    delete files based on age:

    threshold_age = baseline_time - max_age_days

    baseline_time = "YYYY-MM-DDThh:mm:ss"
        or None, which is the same as "Now"

    max_age_days = number of days previous to baseline_time which to retain files

    and remove corresponding row in database
    """
    row_list = db.select_by_age(baseline_time=baseline_time, max_age_days=max_age_days)
    for row in row_list:
        full_fname = os.path.join(row.d['base_data_dir'], row.d['path'], row.d['fname'])
        os.remove(full_fname)
        if row.d['derived_fname'] != 0:
            try:
                os.remove(row.d['derived_fname'])
            except OSError:
                pass
        #end
        db.delete_row(row)
    #end
    print("cull_files_by_age: deleted (%d) files" % len(row_list))
    return len(row_list)

def cull_empty_dirs(base_data_dir):
    """
    execute: 
    find base_data_dir -type d -empty -exec rm {} ;

    returns:
    none
    """
    subprocess.call(['pwd'])
    subprocess.call(['which','find'])
    subprocess.call(['ls',base_data_dir])
    # print empty dirs
    print(['find',base_data_dir,'-type','d','-empty','-print'])
    subprocess.call(['find',base_data_dir,'-type','d','-empty','-print'])

    # delete empty dirs
    # for some reason, rm -rf {} doesn't work under linux
    #subprocess.call(['find',base_data_dir,'-type','d','-empty','-exec','rm','-rf','{}',';'])
    subprocess.call(['find',base_data_dir,'-type','d','-empty','-delete'])


        
def walk_dir_and_load_db(db, base_data_dir='.'):
    """
    search base_data_dir
    delete empty directories
    delete files with specific file extensions
    add remaining files to the database

    returns: number of files added
    """
    cull_files_by_ext(base_data_dir, ext_list=['.avi','.idx','.mp4'])
    cull_empty_dirs(base_data_dir)
    
    num_added = 0
    for dir_path, subdir_list, file_list in os.walk(base_data_dir):
        for fname in file_list:
            # TODO: get mtime
            row = parse_info_amcrest(base_data_dir, dir_path, fname)
            if (row != None):
                db.add_row(row)
                num_added += 1
        #end
    #end
    db.dbconn.commit()
    return num_added


if __name__=="__main__":
    baseline_time = time.strptime("26 feb 2018 00:00", "%d %b %Y %H:%M")
    baseline_time_epoch = time.mktime(baseline_time)
    num_deleted = cull_files(baseline_time_epoch=baseline_time_epoch, max_age_days=1)
    print(num_deleted)
