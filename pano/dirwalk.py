
import os
import time
import subprocess
import datastore
import timeit
import logging
import path_parser

logger = logging.getLogger("pano")

def walk_cam_dir(db, base_data_dir, cam_name, cam_model):
    cam_dir = os.path.join(base_data_dir, cam_name)
    assert os.path.exists(cam_dir)
    parser = path_parser.create(cam_model)
    assert parser, f"unrecognized camera model {cam_model}"

    for dir_path, subdir_list, file_list in os.walk(cam_dir):
        for fname in file_list:
            # >>> dir_path
            # './FTP/cam-00/AMC0028V_795UUB/2021-03-06/001/jpg/12/57'
            # >>> fname
            # '18[M][0@0][0].jpg'
            media_type, ctime = parser.parse(dir_path, fname)
            if media_type != datastore.MEDIA_UNKNOWN:
                row = datastore.Row()
                row.d['base_data_dir'] = base_data_dir
                row.d['cam_name'] = cam_name
                row.d['ctime'] = ctime
                row.d['fname'] = fname
                row.d['mediatype'] = media_type
                row.d['path'] = dir_path[len(base_data_dir)+1:]
                assert row.d['path'][0] != '/'
                db.add_row(row)
            #end
        #end
    #end
    db.commit()


#@timeit.timeit
def cull_files_by_ext(base_data_dir='.', keep_list=['.dav','.jpg','.mp4']):
    logger.info("culling files by extension in %s" % base_data_dir)
    num_deleted = 0
    for dir_path, subdir_list, file_list in os.walk(base_data_dir):
        for fname in file_list:
            full_fname = os.path.join(dir_path, fname)
            (root, ext) = os.path.splitext(fname)  # split foo.bar into 'foo', '.bar'
            if ext not in keep_list:
                logger.info("deleting %s" % fname)
                try:
                    os.remove(full_fname)
                    num_deleted += 1
                except OSError:
                    pass
    return num_deleted
    
#@timeit.timeit
def cull_files_by_age(db, baseline_time='Now', derived_dir='derived',keep_days=14):
    """
    given file entries in db,
    delete files based on age:

    threshold_age = baseline_time - max_age_days

    baseline_time = "YYYY-MM-DDThh:mm:ss"
        or None, which is the same as "Now"

    max_age_days = number of days previous to baseline_time which to retain files

    and remove corresponding row in database

    RETURNS: number of files deleted
    """
    row_list = db.select_older_than(baseline_time=baseline_time, max_age_days=keep_days)
    for row in row_list:
        full_fname = os.path.join(row.d['base_data_dir'], row.d['path'], row.d['fname'])
        try:
            logger.info("deleting %s" % full_fname)
            os.remove(full_fname)
        except OSError:
            logger.warning("failed to remove %s, maxage=(%d) days" % (full_fname, keep_days))
        if row.d['derived_fname'] != 0:
            try:
                os.remove(row.d['derived_fname'])
            except OSError:
                pass
        #end
        db.delete_row(row)
    #end
    logger.info("cull_files_by_age: deleted (%d) files" % len(row_list))
    return len(row_list)

#@timeit.timeit
def cull_empty_dirs(base_data_dir):
    """
    execute: 
    find base_data_dir -type d -empty -exec rm {} ;

    returns:
    none
    """
    logger.info("culling empty dirs in %s" % base_data_dir)
    # print empty dirs
    # print(['find',base_data_dir,'-type','d','-empty','-print'])
    # subprocess.call(['find',base_data_dir,'-type','d','-empty','-print'])

    # delete empty dirs
    # for some reason, rm -rf {} doesn't work under linux
    #subprocess.call(['find',base_data_dir,'-type','d','-empty','-exec','rm','-rf','{}',';'])
    cmd_list = ['find',base_data_dir,'-type','d','-empty','-delete']
    cp=subprocess.run(cmd_list)
    assert cp.returncode==0

#@timeit.timeit        
def walk_dir_and_load_db(db, base_data_dir, cam_name_model_list):
    """
    IN
    db - datastore object
    base_data_dir - base directory containing camera FTP upload directories
    cam_name_model_list - list of tuples, each tuple has form ('camera_name','camera_model')

    OUT
    updated datastore

    returns: number of files added
    """
    assert os.path.exists(base_data_dir)
    # how many entries in db?
    all_rows = db.select_all()
    num_start = len(all_rows)

    assert isinstance(cam_name_model_list, list)
    assert len(cam_name_model_list[0])==2

    for cam_name, cam_model in cam_name_model_list:
        walk_cam_dir(db, base_data_dir, cam_name, cam_model)
    #end

    all_rows = db.select_all()
    num_stop = len(all_rows)
    assert num_start <= num_stop
    num_added = num_stop - num_start
    
    return num_added


if __name__=="__main__":
    baseline_time = time.strptime("26 feb 2018 00:00", "%d %b %Y %H:%M")
    baseline_time_epoch = time.mktime(baseline_time)
    num_deleted = cull_files(baseline_time_epoch=baseline_time_epoch, max_age_days=1)
    print(num_deleted)
