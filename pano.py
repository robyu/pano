#!/usr/bin/env python
import json
import datastore
import dirwalk
import os
import webpage
import derived
import indexpage
import click
import time
import timeit

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
    cam_page_fname_list=[]
    
    def __init__(self, config_fname):
        print("Pano: reading config file (%s)" % config_fname)
        self.param_dict = self.init_param_dict(config_fname)

        if self.param_dict['drop_table_flag']==0:
            drop_table_flag=False
        else:
            drop_table_flag=True
        #end 
        self.image_db = datastore.Datastore(self.param_dict['database_fname'],
                                            drop_table_flag=drop_table_flag)

    def init_param_dict(self, config_fname):
        """
        read user-specified config file, default config file,
        merge the two parameters

        returns:
        merged parameter dict
        """
        #
        # read config json, store in dict
        f = open(self.default_json_fname)
        defaults_dict = json.load(f)
        f.close()

        f = open(config_fname)
        user_param_dict = json.load(f)
        f.close()
        
        merged_dict = self.merge_dicts(defaults_dict, user_param_dict)
        return merged_dict
        
    def merge_dicts(self, defaults_dict, user_dict):
        """
        given defaults_dict and user_dict,
        compare keys and pick appropriate value.
        assert if value is bogus.

        return merged dict
        """
        merged_dict={}
        for k, default_val in defaults_dict.items():
            if k[0]=='@':
                #
                # the key is a comment
                continue
            
            if k in user_dict:
                final_val = user_dict[k]
            else:
                final_val = default_val
            #end
            assert (final_val != "") , "parameter (%s) not assigned" % k
            merged_dict[k] = final_val
        #end

        assert len(merged_dict['camera_list']) > 0, "no cameras listed"
        assert len(merged_dict['base_data_dir']) > 0, "no base_data_dir specified"
        assert merged_dict['delta_min'] > 0, "delta min < 0"
        assert merged_dict['max_age_days'] > 0, "max_age_days < 0"

        return merged_dict

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

    def get_cam_list(self):
        """
        return list of camera names extracted from param_dict
        """
        cam_list = self.param_dict['camera_list']
        return cam_list
    
    def gen_index_page(self):
        print("** generate index page")
        assert len(self.cam_page_fname_list) > 0, "you gotta run gen_camera_pages first"
        cam_list = self.get_cam_list()

        assert len(cam_list) == len(self.cam_page_fname_list)
        index_page = indexpage.IndexPage()
        index_fname = index_page.make_index(self.cam_page_fname_list, cam_list)
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
        num_deleted = dirwalk.cull_files_by_age(self.image_db,
                                  derived_dir = self.param_dict['derived_dir'],
                                  baseline_time = self.param_dict['baseline_datetime'],
                                  max_age_days = self.param_dict['max_age_days'])
        return num_deleted
    
    @timeit.timeit
    def gen_camera_pages(self, make_derived_files=True):
        """
        for each camera listed in the json file, 
        cull files by age
        generate derivative media files (thumbnails, etc)
        generate a webpage 

        returns:
        list of camera webpage filenames
        """
        print("** generate camera webpages")
        print("*** make derived files")
        if (make_derived_files==True):
            derived.make_derived_files(self.image_db,
                                       num_workers = self.param_dict['num_worker_threads'],
                                       derived_dir = self.param_dict['derived_dir'])
        #endif
        
        cam_list = self.get_cam_list()

        if os.path.exists(self.param_dict['www_dir'])==False:
            os.mkdir(self.param_dict['www_dir'])

        cam_page_fname_list=[]
        print("*** write webpages")
        for index in range(len(cam_list)):
            cam_page_fname =  'cam_%02d.html' % index
            cam_name = cam_list[index]['name']
            cam_page = webpage.Webpage(os.path.join(self.param_dict['www_dir'], cam_page_fname),
                                       cam_name,
                                       self.param_dict['derived_dir'],
                                       self.param_dict['base_data_dir'])
            cam_page.make_webpage(self.param_dict['baseline_datetime'],
                                  self.param_dict['max_age_days'],
                                  self.param_dict['delta_min'],
                                  self.image_db)
            cam_page_fname_list.append(cam_page_fname)
        #end
        self.cam_page_fname_list = cam_page_fname_list
        return cam_page_fname_list

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
def pano_main(config, loopcnt):
    print("config file=%s" % config)
    print("loopcnt=%d" % loopcnt)
    mypano = Pano(config)
    loop_flag = True
    loop_index=0
    while loop_flag:
        num_entries_start = len(mypano.image_db.select_all())
        (num_files_added, num_deleted_ext) = mypano.slurp_images()
        num_deleted_age = mypano.cull_old_files()
        cam_page_fname_list = mypano.gen_camera_pages()
        index_fname = mypano.gen_index_page()
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
    
