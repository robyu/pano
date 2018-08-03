import os
import time
import subprocess
import datastore
import multiprocessing as mp
import sys
import timeit


DEFAULT_DERIVED_DIR = './derived'

def convert_dav_to_mp4(base_data_dir, path, fname, derived_dir,print_cmd_flag=False):
    src_fname = os.path.join(base_data_dir, path, fname)
    dest_path = os.path.join(derived_dir, path)
    dest_fname = os.path.join(dest_path, fname)
    dest_fname = dest_fname.replace('.dav','.mp4')

    #
    # dont assert src existence--file may have been deleted?!
    #assert os.path.exists(src_fname)
    
    try:
        os.makedirs(dest_path)
    except os.error:
        pass

    if os.path.exists(dest_fname)==True:
        print("%s -> %s already exists" % (src_fname, dest_fname))
    else:        
        capture_file = open("ffmpeg_out.txt","wt")
        # ffmpeg -i 21.18.33-21.26.00\[M\]\[0\@0\]\[0\].dav -vcodec copy -preset veryfast out2.avi
        cmd = ['ffmpeg', '-y','-i',src_fname, '-vcodec', 'copy', '-preset', 'veryfast', dest_fname]
        if print_cmd_flag==True:
            print(cmd)
        #end
        subprocess.call(cmd,stdout=capture_file, stderr=capture_file)
        capture_file.close()

        # check again: conversion may have failed
        if os.path.exists(dest_fname)==False:
            print("%s -> %s failed" % (src_fname, dest_fname))
            dest_fname=''  # if failed, then return empty string
            assert len(dest_fname)==0
        else:
            print("%s -> %s success" % (src_fname, dest_fname))
        #end 
    #end
    return dest_fname

def make_thumbnail(base_data_dir, path, fname, derived_dir,print_cmd_flag=False):
    """
    given the base_data_dir+path+fname of an image,
    generate a thumbnail image in derived_dir,

    returns the absolute filename of the thumbnail
    """
    src_fname = os.path.join(base_data_dir, path, fname)
    dest_path = os.path.join(derived_dir, path)
    dest_fname = os.path.join(dest_path, fname)
    assert os.path.exists(src_fname)
    try:
        os.makedirs(dest_path)
    except os.error:
        pass

    if os.path.exists(dest_fname)==True:
        print("%s -> %s already exists" % (src_fname, dest_fname))
    else:        
        #
        # dont need to check beforehand if the dest_fname already exists,
        # because we wouldn't be calling this function if derived_failed == 1

        cmd = ['convert',src_fname, '-resize', '10%',dest_fname]
        if print_cmd_flag==True:
            print(cmd)
        #end
        subprocess.call(cmd)

        if os.path.exists(dest_fname)==False:
            print("%s -> %s failed" % (src_fname, dest_fname))
            dest_fname=''  # if failed, then return empty string
            assert len(dest_fname)==0
        else:
            print("%s -> %s success" % (src_fname, dest_fname))
        #end
    #end    
    return dest_fname

def sleep_fcn(row, derived_dir):
    """
    given datastore row and output directory name (derived_dir),
    
    sleep a bit, then return bogus results
    """
    time.sleep(0.1)
    print("%s -> %s...FAILED" % (row.d['fname'], os.path.join(derived_dir, row.d['fname'])))

    return_dict={}
    return_dict['id'] = row.d['id']
    return_dict['derived_fname'] = ''   # pretend that derivative process failed
    return return_dict

def process_media_file(row, derived_dir):
    """
    given datastore row and output directory name (derived_dir),
    
    return dictionary:
    'id' = id of processed database entry
    'derived_fname' = filename of generated media file (== '' if failed)
    """
    # print("process_media_file: id=%d derive_failed=%d derived_fname=%s fname=%s" % (row.d['id'],
    #                                                                    row.d['derive_failed'],
    #                                                                    row.d['derived_fname'],
    #                                                                    row.d['fname']))
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
    

@timeit.timeit
def derive_with_threads(num_workers, db, derived_dir, row_list, test_thread_flag):
    """
    run media processing functions 
    in worker pool threads

    process each file in row_list to generate derived file (thumbnail, etc)
    
    update database with resulting filename, success status

    return (# success, # failed)

    """
    MAX_WAIT_SEC = 60 *2 
    assert num_workers >= 1
    pool = mp.Pool(num_workers)
    index=0
    count_success=0
    count_failed =0

    #
    # assign only as many workers as specified (pool.apply_async) before
    # waiting for the results (mpr.get) because
    # we want to regularly update the database with the pass/fail results
    while index < len(row_list):
        mpr_list = []
        
        # assign media file to each worker
        worker_index=0
        while worker_index < num_workers:
            if index >= len(row_list):
                #
                # exit loops
                break
            else:
                assert index < len(row_list)
                row = row_list[index]
                index += 1
                if row.d['derive_failed']==0 and len(row.d['derived_fname'])==0:
                    if test_thread_flag==True:
                            #
                            # run a fake test fcn, just to test thread pool
                        mpr = pool.apply_async(sleep_fcn, args=(row, derived_dir))
                    else:
                        mpr = pool.apply_async(process_media_file, args=(row, derived_dir))
                        #print("assigned row %d to worker %d" % (index, n))
                    #end  
                    mpr_list.append(mpr)
                    worker_index += 1
                #end
            #end
        #end

        # marshall workers
        for mpr in mpr_list:
            try:
                result_dict = mpr.get(MAX_WAIT_SEC)
                # update datastore with derived fname
                if len(result_dict['derived_fname']) > 0:
                    db.update_row(result_dict['id'], 'derived_fname', result_dict['derived_fname'])
                    count_success += 1
                else:
                    count_failed += 1
                    db.update_row(result_dict['id'], 'derive_failed', 1)
                #end
            except mp.TimeoutError:
                count_failed += 1
                db.update_row(result_dict['id'], 'derive_failed', 1)
            #end
        
        #end
    #end
    return (count_success, count_failed)
    
    
@timeit.timeit
def derive_with_single_thread(db, derived_dir, row_list, test_thread_flag):
    """
    process each file in row_list to generate derived file (thumbnail, etc)
    
    update database with resulting filename, success status

    return (# success, # failed)
    """
    count_success = 0
    count_failed = 0
    for row in row_list:
        if row.d['derive_failed']==0 and len(row.d['derived_fname'])==0:
            if test_thread_flag==True:
                result_dict = sleep_fcn(row, derived_dir)
            else:
                result_dict = process_media_file(row, derived_dir)
            #end

            if len(result_dict['derived_fname']) > 0:
                db.update_row(result_dict['id'], 'derived_fname', result_dict['derived_fname'])
                count_success += 1
            else:
                count_failed += 1
                db.update_row(result_dict['id'], 'derive_failed', 1)
            #end 
        #end
    #end
    return (count_success, count_failed)

@timeit.timeit
def make_derived_files(db, derived_dir=DEFAULT_DERIVED_DIR, num_workers = -1, test_thread_flag=False):
    """
    create directory for derived files.
    for each entry in database, create derived files (thumbnails, converted video)
    populate the derived fname column

    returns (count_success, count_failed)
    """
    try:
        os.mkdir(derived_dir)
    except OSError:
        pass

    #
    # previous mkdir could fail for a number of reasons, but make sure the directory
    # actually exists
    assert os.path.exists(derived_dir)
        
    row_list = db.select_all()

    if num_workers <= 0:
        num_workers = mp.cpu_count()
    print("make_derived_files: num_workers=%d" % num_workers)

    assert num_workers >= 1
    
    if num_workers >= 2:
        count_success, count_failed = derive_with_threads(num_workers, db, derived_dir, row_list, test_thread_flag)
    else:
        count_success, count_failed = derive_with_single_thread(db, derived_dir, row_list, test_thread_flag)
        
    print("success=%d failed=%d" % (count_success, count_failed))
    print("done with make_derived_files")
    return (count_success, count_failed)
    
