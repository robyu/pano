
import os
import time
import subprocess
import datastore

DERIVED_DIR='derived'

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
    if len(dir_element_list) < 6:
        return None

    row = datastore.Row()
    row.d['path'] = dir_path
    row.d['fname'] = fname
    if dir_element_list[4]=='jpg' and fname[-3:len(fname)]=='jpg':
        row = parse_info_amcrest_jpg(row, dir_element_list, fname)
    elif dir_element_list[4]=='dav' and fname[-3:len(fname)]=='dav':
        row = parse_info_amcrest_dav(row, dir_element_list, fname)
    else:
        #print('dont know how to handle %s %s' % (row.d['path'], row.d['fname']))
        return None
    return row
    
def cull_files_by_ext(root_dir='.', ext_list=['.avi','.idx']):
    num_deleted = 0
    for dir_path, subdir_list, file_list in os.walk(root_dir):
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
    

def cull_files_by_age(db, root_dir='.',baseline_time=None, derived_dir=DERIVED_DIR,max_age_days=14):
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
        full_fname = os.path.join(root_dir, row.d['path'], row.d['fname'])
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


def convert_dav_to_mp4(root_dir, path, fname, derived_dir):
    src_fname = os.path.join(root_dir, path, fname)
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

def make_thumbnail(root_dir, path, fname, derived_dir):
    """
    given the root_dir+path+fname of an image,
    generate a thumbnail image in derived_dir,

    returns the absolute filename of the thumbnail
    """
    src_fname = os.path.join(root_dir, path, fname)
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
    
def make_derived_files(db, root_dir='.', derived_dir=DERIVED_DIR):
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
            derived_fname=convert_dav_to_mp4(root_dir, row.d['path'], row.d['fname'], derived_dir)
        elif row.d['mediatype']==datastore.MEDIA_IMAGE:
            derived_fname=make_thumbnail(root_dir, row.d['path'], row.d['fname'], derived_dir)
        else:
            assert False, "mediatype (%s) not recognized" % row.d['mediatype']

        # set entry's derived column
        db.update_row(row.d['id'], 'derived_fname', derived_fname)
        if len(derived_fname)==0:
            print("could not create derived file for row id [%d]" % row.d['id'])
        
    return
        
def walk_dir_and_load_db(db, root_dir='.'):
    """
    search root_dir
    delete empty directories
    delete files with specific file extensions
    add remaining files to the database

    returns: number of files added
    """
    cull_files_by_ext(root_dir, ext_list=['.avi','.idx','.mp4'])
    cull_empty_dirs(root_dir)
    
    num_added = 0
    for dir_path, subdir_list, file_list in os.walk(root_dir):
        for fname in file_list:
            # TODO: get mtime
            row = parse_info_amcrest(root_dir, dir_path, fname)
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
