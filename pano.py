#!/usr/bin/env python
import json
import datastore
import dirwalk
import os
import campage
import derived
import indexpage
import click
import time
import timeit
import subprocess
import pudb
import panoconfig

"""
data dict
=========
database file = panodb.sqlite
camera_list = [[name:'b0',
                live_url:'http://192.168.0.1'],
                description:'porch',

               [name:'b1',
                live_url:'http://192.168.0.1'
                description:'porch']]

base_data_dir = 'testdata/FTP'
delta_min = 10
max_age_days = 14
www_dir = 'www'
baseline_datetime='now'
cull_old_files = yes

"""
class Pano:
    default_json_fname = "pano_defaults.json"
    param_dict = {}
    image_db = None
    
    def __init__(self, config_fname,droptable=False):
        print("Pano: reading config file (%s)" % config_fname)
        self.param_dict = panoconfig.get_param_dict(config_fname)

        self.generate_sym_links()
        
        if self.param_dict['drop_table_flag']==0 and droptable==False:
            drop_table_flag=False
        else:
            print("drop existing table")
            drop_table_flag=True
        #end 
        self.image_db = datastore.Datastore(self.param_dict['database_fname'],
                                            drop_table_flag=drop_table_flag)

    def generate_sym_links(self):
        """
        generate links in www directory to data directories
        """
        assert os.path.exists(self.param_dict['www_dir'])

        data_dir_abs_path = os.path.realpath(self.param_dict['base_data_dir'])
        assert os.path.exists(data_dir_abs_path)

        www_base_dir = os.path.join(self.param_dict['www_dir'], self.param_dict['www_base_dir'])
        if os.path.exists(www_base_dir)==True:
            os.unlink(www_base_dir)
            
        os.symlink(data_dir_abs_path, www_base_dir)

        derived_dir_abs_path = os.path.realpath(self.param_dict['derived_dir'])
        assert os.path.exists(derived_dir_abs_path)

        www_derived_dir = os.path.join(self.param_dict['www_dir'], self.param_dict['www_derived_dir'])
        if os.path.exists(www_derived_dir)==True:
            os.unlink(www_derived_dir)
            
        os.symlink(derived_dir_abs_path, www_derived_dir)

    @timeit.timeit
    def slurp_images(self):
        """
        given base_data_dir,
        - delete empty dirs
        - delete files with specific extensions
        - walk over dir tree and store image files in db

        returns
        (number of files added, number files deleted by filename extension)
        """
        total_files_added = 0
        total_files_deleted = 0
        print("** slurp images")
        base_data_dir = self.param_dict['base_data_dir']
        cam_list = self.get_cam_list()
        for cam in cam_list:
            cam_dir = os.path.join(base_data_dir, cam['name']) # "testdata/FTP-culled/b0"
            print("*** processing camera dir %s" % cam_dir)
            print("**** cull empty dirs")
            dirwalk.cull_empty_dirs(cam_dir)
            print("**** cull files by ext")
            num_deleted = dirwalk.cull_files_by_ext(base_data_dir=cam_dir)
            print("**** walk dir and load db")
            num_added = dirwalk.walk_dir_and_load_db(self.image_db, base_data_dir,
                                                           cam_name = cam['name'])
            total_files_added += num_added
            total_files_deleted += num_deleted
        #end
        return (total_files_added, total_files_deleted)

    def normalize_cam_name(self, name):
        """
        normalize camera name wrt white spaces, etc
        idempotent!

        returns: normalized cam name
        """
        name = name.replace(' ','-')
        name = name.lower()

        assert len(name) <= 20, "camera name (%s) > 20 chars" % name
        return name
    
    def get_cam_list(self):
        """
        return list of camera info from param_dict
        """
        cam_list = self.param_dict['camera_list']

        return cam_list
    
    def gen_index_page(self, cam_list):
        """
        IN:
        cam_list: list of per-camera dict objects
        """
        print("** generate index page")
        assert len(cam_list) > 0, "you gotta run gen_camera_pages first"
        
        index_page = indexpage.IndexPage(self.param_dict['www_dir'])
        index_fname = index_page.make_index(cam_list)
        return index_fname

    @timeit.timeit
    def cull_old_files(self):
        """
        search through datastore, find old entries and delete entries
        and corresponding media files

        returns:
        num entries deleted
        """
        print("** cull files by age")
        if self.param_dict['cull_old_files']==1:
            num_deleted = dirwalk.cull_files_by_age(self.image_db,
                                                    derived_dir = self.param_dict['derived_dir'],
                                                    baseline_time = self.param_dict['baseline_datetime'],
                                                    max_age_days = self.param_dict['max_age_days'])
        else:
            num_deleted = 0
        #END
        
        return num_deleted
    

    def gen_camera_pages(self, make_derived_files=True):
        """
        for each camera listed in the json file, 
        cull files by age
        generate derivative media files (thumbnails, etc)
        generate a webpage 

        returns:
        list of dictionary elements, where each element is
        the camera-info list (see get_cam_list) plus an extra entry, "status_page_list"
        listing the web pages
        """
        print("** generate camera webpages")
        print("*** make derived files")
        if (make_derived_files==True):
            derived.make_derived_files(self.image_db,
                                       num_workers = self.param_dict['num_worker_threads'],
                                       derived_dir = self.param_dict['derived_dir'])
        #endif
        
        cam_list = self.get_cam_list()

        assert  os.path.exists(self.param_dict['www_dir'])

        #
        # delete old cam pages
        subprocess.call(['find',self.param_dict['www_dir'],'-type','f','-name','cam*.html','-delete'])
        #pu.db
        print("*** write webpages")
        for index in range(len(cam_list)):
            cam_page_base_fname =  'cam_%02d' % index  # webpage generator will add suffix + .html

            #
            # get camera name
            # we dont normalize camera name until now because we assume the media
            # file paths use the unnormalized camera names
            cam_name = cam_list[index]['name']
            cam_name = self.normalize_cam_name(cam_name)
            page_generator = campage.CamPage(cam_name,
                                             self.image_db,
                                             self.param_dict['derived_dir'],
                                             self.param_dict['base_data_dir'],
                                             self.param_dict['www_dir'],
                                             self.param_dict['www_derived_dir'],
                                             self.param_dict['www_base_dir'])
                                             
            # generate 1 or more HTML webpages
            status_page_list = page_generator.generate(self.param_dict['baseline_datetime'],
                                                       self.param_dict['max_age_days'],
                                                       self.param_dict['delta_min'])

            #
            # augment the existing dictionary list to add the filenames
            cam_list[index]['status_page_list'] = status_page_list    # formerly page_fnames_list
            #end
        #end
        return cam_list

    def sleep(self):
        assert self.param_dict['sleep_interval_min'] > 0.0
        sleep_interval_sec = 60.0 * self.param_dict['sleep_interval_min']
        time.sleep(sleep_interval_sec)
        return


    def print_summary(self, num_added, num_deleted_ext, num_deleted_age,num_entries_start):
        print("== SUMMARY ==")
        print("CAMERAS:")
        cam_list = self.get_cam_list()
        for cam in cam_list:
            print("%s" % cam['name'])
        #end
        print("")
        print("FILE PROCESSING:")
        print("Files Deleted (wrong extension): %d" % num_deleted_ext)
        print("Files Added: %d" % num_added)
        print("")
        print("DATASTORE:")
        print("Num Entries before processing: %d" % num_entries_start)
        print("Num Entries deleted (age): %d" % num_deleted_age)
        all_rows = self.image_db.select_all()
        print("Num Entries after processing: %d" % len(all_rows))
        
        return
    
@click.command()
@click.argument('config')
@click.option('--loopcnt',default=-1,help='number of times to loop; -1 == forever')
@click.option('--droptable/--no-droptable', default=False,help='delete existing image database')
def pano_main(config, loopcnt,droptable):
    print("config file=%s" % config)
    print("loopcnt=%d" % loopcnt)
    mypano = Pano(config,droptable)
    loop_flag = True
    loop_index=0
    while loop_flag:
        num_entries_start = len(mypano.image_db.select_all())
        (num_files_added, num_deleted_ext) = mypano.slurp_images()
        num_deleted_age = mypano.cull_old_files()
        #pu.db
        cam_list = mypano.gen_camera_pages()
        index_fname = mypano.gen_index_page(cam_list)
        mypano.print_summary(num_files_added, num_deleted_ext, num_deleted_age, num_entries_start)
        print("sleeping...%6.2f min" % mypano.param_dict['sleep_interval_min'])
        mypano.sleep()

        loop_index += 1
        if (loopcnt >= 0):
            loop_flag = loop_index < loopcnt
        else:
            loop_flag = True
        #end
    #end

if __name__=="__main__":
    pano_main()
    
