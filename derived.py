import os
import time
import subprocess
import datastore
import multiprocessing as mp

DERIVED_DIR='derived'

def convert_dav_to_mp4(base_data_dir, path, fname, derived_dir):
    src_fname = os.path.join(base_data_dir, path, fname)
    dest_path = os.path.join(derived_dir, path)
    dest_fname = os.path.join(dest_path, fname)
    dest_fname = dest_fname.replace('.dav','.mp4')
    dest_fname = os.path.abspath(dest_fname)
    assert os.path.exists(src_fname)
    try:
        os.makedirs(dest_path)
    except os.error:
        pass

    if os.path.exists(dest_fname)==False:
        # ffmpeg -i 21.18.33-21.26.00\[M\]\[0\@0\]\[0\].dav -vcodec copy -preset veryfast out2.avi
        cmd = ['ffmpeg', '-y','-i',src_fname, '-vcodec', 'copy', '-preset', 'veryfast', dest_fname]
        subprocess.call(cmd)

    # check again: conversion may have failed
    if os.path.exists(dest_fname)==False:
        dest_fname=''  # if failed, then return empty string
        
    return dest_fname

def make_thumbnail(base_data_dir, path, fname, derived_dir):
    """
    given the base_data_dir+path+fname of an image,
    generate a thumbnail image in derived_dir,

    returns the absolute filename of the thumbnail
    """
    src_fname = os.path.join(base_data_dir, path, fname)
    dest_path = os.path.join(derived_dir, path)
    dest_fname = os.path.join(dest_path, fname)
    dest_fname = os.path.abspath(dest_fname)
    assert os.path.exists(src_fname)
    try:
        os.makedirs(dest_path)
    except os.error:
        pass

    if os.path.exists(dest_fname)==False:
        cmd = ['magick','convert',src_fname, '-resize', '10%',dest_fname]
        subprocess.call(cmd)

    if os.path.exists(dest_fname)==False:
        dest_fname=''  # if failed, then return empty string
    
    return dest_fname

def sleep_fcn(row, derived_dir):
    """
    given datastore row and output directory name (derived_dir),
    
    sleep a bit, then return bogus results
    """
    time.sleep(1)
    print("%s %s" % (row.d['fname'], derived_dir))

    return_dict={}
    return_dict['id'] = row.d['id']
    return_dict['derived_fname'] = 'foobar'
    return return_dict

def process_media_file(row, derived_dir):
    """
    given datastore row and output directory name (derived_dir),
    
    return dictionary:
    'id' = id of processed database entry
    'derived_fname' = filename of generated media file (== '' if failed)
    """
    print("%s %s" % (row.d['fname'], derived_dir))

    if row.d['mediatype']==datastore.MEDIA_VIDEO:
        derived_fname=convert_dav_to_mp4(row.d['base_data_dir'], row.d['path'], row.d['fname'], derived_dir)
    elif row.d['mediatype']==datastore.MEDIA_IMAGE:
        derived_fname=make_thumbnail(row.d['base_data_dir'], row.d['path'], row.d['fname'], derived_dir)
    else:
        print("(%s) has unrecognized mediatype (%d)" % (media_fname, media_type))
        derived_fname = None
    #endif
    return_dict={}
    return_dict['id'] = row.d['id']
    return_dict['derived_fname'] = derived_fname
    return return_dict
    

def OLDmake_derived_files(db, base_data_dir='.', derived_dir=DERIVED_DIR):
    """
    create directory for derived files.
    for each entry in database, create derived files (thumbnails, converted video)
    populate the derived fname column
    """
    try:
        os.mkdir(os.path.join('.',derived_dir))
    except OSError:
        print("derived dir (%s) already exists" % derived_dir)
        
    row_list = db.select_all()
    for row in row_list:
        if row.d['mediatype']==datastore.MEDIA_VIDEO:
            derived_fname=convert_dav_to_mp4(base_data_dir, row.d['path'], row.d['fname'], derived_dir)
        elif row.d['mediatype']==datastore.MEDIA_IMAGE:
            derived_fname=make_thumbnail(base_data_dir, row.d['path'], row.d['fname'], derived_dir)
        else:
            assert False, "mediatype (%s) not recognized" % row.d['mediatype']

        # set entry's derived column
        db.update_row(row.d['id'], 'derived_fname', derived_fname)
        if len(derived_fname)==0:
            print("could not create derived file for row id [%d]" % row.d['id'])
        
    return


def derive_with_threads(num_workers, db, derived_dir, row_list, test_thread_flag):
    """
    run media processing functions 
    in worker pool threads
    """
    MAX_WAIT_SEC = 60 *2 
    assert num_workers >= 1
    pool = mp.Pool(num_workers)
    mpr_list = []
    for row in row_list:
        if test_thread_flag==True:
            #
            # run a fake test fcn, just to test thread pool
            mpr = pool.apply_async(sleep_fcn, args=(row, derived_dir))
        else:
            mpr = pool.apply_async(process_media_file, args=(row, derived_dir))
        mpr_list.append(mpr)

    for mpr in mpr_list:
        try:
            result_dict = mpr.get(MAX_WAIT_SEC)
            # update datastore with derived fname
            if len(result_dict['derived_fname']) > 0:
                db.update_row(result_dict['id'], 'derived_fname', result_dict['derived_fname'])
        except mp.TimeoutError:
            pass
    
    
def make_derived_files(db, base_data_dir='.', derived_dir=DERIVED_DIR, num_workers = -1, test_thread_flag=False):
    """
    create directory for derived files.
    for each entry in database, create derived files (thumbnails, converted video)
    populate the derived fname column
    """
    try:
        os.mkdir(os.path.join('.',derived_dir))
    except OSError:
        print("derived dir (%s) already exists" % derived_dir)
        
    row_list = db.select_all()

    if num_workers <= 0:
        num_workers = mp.cpu_count()

    assert num_workers >= 1
    
    if num_workers >= 2:
        derive_with_threads(num_workers, db, derived_dir, row_list, test_thread_flag)
    else:
        #
        # for 1 thread, do not use worker pool (to save memory)
        for row in row_list:
            if test_thread_flag==True:
                result_dict = sleep_fcn(row, derived_dir)
            else:
                result_dict = process_media_file(row, derived_dir)
            #end

            if len(result_dict['derived_fname']) > 0:
                db.update_row(result_dict['id'], 'derived_fname', result_dict['derived_fname'])
            #end
        #end
    #end
    print("done with derived files")
    
