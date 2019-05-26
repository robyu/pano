#!/usr/bin/env python3
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
import datetime
import logging
import logging.handlers
import sys

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
    logger = None
    
    def __init__(self, config_fname,droptable=False, loglevel='warning', logfname='stdout'):
        print("Pano: reading config file (%s)" % config_fname)
        self.logger = self.configure_logging(loglevel, logfname)
        self.param_dict = panoconfig.get_param_dict(config_fname)

        self.generate_sym_links()
        
        if self.param_dict['drop_table_flag']==0 and droptable==False:
            drop_table_flag=False
        else:
            self.logger.info("drop existing table")
            drop_table_flag=True
        #end 
        self.image_db = datastore.Datastore(self.param_dict['database_fname'],
                                            drop_table_flag=drop_table_flag)

        cam_list = self.get_cam_list()
        self.logger.info("REGISTERED CAMERAS:")
        for cam in cam_list:
            self.logger.info(cam['name'])
        #end

    def configure_logging(self, loglevel,logfname):
        """
        see https://docs.python.org/2/howto/logging.html
        
        but see also
        https://stackoverflow.com/questions/20240464/python-logging-file-is-not-working-when-using-logging-basicconfig
        """
        #logger = logging.getLogger("app")
        logger = logging.getLogger()

        #
        # normalize loglevel arg
        #
        # assuming loglevel is bound to the string value obtained from the
        # command line argument. Convert to upper case to allow the user to
        # specify --log=DEBUG or --log=debug
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        if logfname=='stdout':
            print("logging to stdout")
            handler = logging.StreamHandler(sys.stdout)
        else:
            print("logging to %s" % logfname)
            handler = logging.handlers.RotatingFileHandler(logfname, maxBytes=128000, backupCount=4)
        #end
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
        handler.setFormatter(formatter)        
        logger.addHandler(handler)

        # because of how logging is imported,    
        # can't set level of root logger using basicConfig
        # see stackoverflow question above
        logger.setLevel(numeric_level)


        logger.debug("DEBUG logging enabled")
        logger.info("INFO logging enabled")
        logger.warning("WARNING logging enabled")
        logger.error("ERROR logging enabled")
        logger.critical("CRITICAL logging enabled")

        return logger
        
    @timeit.timeit
    def generate_sym_links(self):
        """
        generate links in www directory to data directories
        """
        assert os.path.exists(self.param_dict['www_dir']), "%s does not exist" % self.param_dict['www_dir']

        data_dir_abs_path = os.path.realpath(self.param_dict['base_data_dir'])
        assert os.path.exists(data_dir_abs_path), "%s does not exist" % data_dir_abs_path

        www_base_dir = os.path.join(self.param_dict['www_dir'], self.param_dict['www_base_dir'])
        if os.path.exists(www_base_dir)==True:
            os.unlink(www_base_dir)
            
        os.symlink(data_dir_abs_path, www_base_dir)

        derived_dir_abs_path = os.path.realpath(self.param_dict['derived_dir'])
        assert os.path.exists(derived_dir_abs_path), "%s does not exist" % derived_dir_abs_path

        www_derived_dir = os.path.join(self.param_dict['www_dir'], self.param_dict['www_derived_dir'])
        if os.path.exists(www_derived_dir)==True:
            os.unlink(www_derived_dir)
            
        os.symlink(derived_dir_abs_path, www_derived_dir)

    @timeit.timeit
    def slurp_images(self, skip_flag=False):
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
        self.logger.info("** slurp images")

        if skip_flag:
            self.logger.debug("skipping slurp")
            return (total_files_added, total_files_deleted)
        #endif
        
        base_data_dir = self.param_dict['base_data_dir']
        cam_list = self.get_cam_list()
        for cam in cam_list:
            cam_dir = os.path.join(base_data_dir, cam['name']) # "testdata/FTP-culled/b0"
            self.logger.debug("*** processing camera dir %s" % cam_dir)
            num_deleted = dirwalk.cull_files_by_ext(base_data_dir=cam_dir)
            num_added = dirwalk.walk_dir_and_load_db(self.image_db, base_data_dir,
                                                           cam_name = cam['name'])
            total_files_added += num_added
            total_files_deleted += num_deleted
        #end
        return (total_files_added, total_files_deleted)

    @timeit.timeit
    def cull_empty_dirs(self, skip_flag=False):
        """
        """
        self.logger.info("delete empty dirs")

        if skip_flag:
            return
        #endif

        # delete empty dirs in the data directory, e.g. FTP/cam00
        base_data_dir = self.param_dict['base_data_dir']
        derived_dir = self.param_dict['derived_dir']
        cam_list = self.get_cam_list()
        for cam in cam_list:
            cam_dir = os.path.join(base_data_dir, cam['name']) # "testdata/FTP-culled/b0"
            self.logger.debug("cull empty dirs %s" % cam_dir)
            dirwalk.cull_empty_dirs(cam_dir)

            cam_dir = os.path.join(derived_dir, cam['name'])
            self.logger.debug("cull empty dirs %s" % cam_dir)
            dirwalk.cull_empty_dirs(cam_dir)
        #end

        return

    def cull_and_sleep(self, skip_cull_flag=False):
        sleep_sec = self.param_dict['sleep_interval_min'] * 60.0

        cull_start = time.time()
        self.cull_empty_dirs(skip_cull_flag)
        cull_stop = time.time()

        remaining_sec = max(sleep_sec - (cull_stop - cull_start), 0.0)
        assert remaining_sec >= 0.0
        self.logger.debug("sleep for remaining %f sec" % remaining_sec)
        time.sleep(remaining_sec)
        return

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
    
    @timeit.timeit
    def gen_index_page(self, cam_list):
        """
        IN:
        cam_list: list of per-camera dict objects
        """
        self.logger.info("** generate index page")
        assert len(cam_list) > 0, "you gotta run gen_camera_pages first"
        
        index_page = indexpage.IndexPage(self.image_db,
                                         self.param_dict['www_dir'],
                                         self.param_dict['derived_dir'],
                                         self.param_dict['www_derived_dir'])
        index_fname = index_page.make_index(cam_list)
        return index_fname

    @timeit.timeit
    def cull_old_files(self, skip_flag):
        """
        search through datastore, find old entries and delete entries
        and corresponding media files

        returns:
        num entries deleted
        """
        self.logger.info("** cull files by age")
        if skip_flag:
            num_deleted = 0
        else:
            num_deleted = dirwalk.cull_files_by_age(self.image_db,
                                                    derived_dir = self.param_dict['derived_dir'],
                                                    baseline_time = self.param_dict['baseline_datetime'],
                                                    max_age_days = self.param_dict['max_age_days'])
        #END
        return num_deleted
    
    @timeit.timeit
    def derive_media(self, skip_flag=False):
        """
        for each camera listed in the json file, 
        generate derivative media files (thumbnails, etc)

        returns:
        none
        """
        self.logger.info("** make derived media")
        if skip_flag:
            return
        #end
        
        cam_list = self.get_cam_list()

        for index in range(len(cam_list)):
            cam_name = cam_list[index]['name']

            derived.make_derived_files(self.image_db,
                                       cam_name,
                                       num_workers = self.param_dict['num_worker_threads'],
                                       derived_dir = self.param_dict['derived_dir'])

        #end
        return

    @timeit.timeit
    def gen_camera_pages(self, skip_flag=False):
        """
        for each camera listed in the json file, 
        generate a webpage 

        returns:
        list of dictionary elements, where each element is
        the camera-info list (see get_cam_list) plus an extra entry, "status_page_list"
        listing the web pages
        """
        self.logger.info("** generate camera webpages")

        cam_list = self.get_cam_list()

        assert  os.path.exists(self.param_dict['www_dir'])

        for index in range(len(cam_list)):
        
            cam_page_base_fname =  'cam_%02d' % index  # webpage generator will add suffix + .html

            cam_name = cam_list[index]['name']


            #
            # get camera name
            # we dont normalize camera name until now because we assume the media
            # file paths use the unnormalized camera names
            norm_cam_name = self.normalize_cam_name(cam_name)
            page_generator = campage.CamPage(norm_cam_name,
                                             self.image_db,
                                             self.param_dict['derived_dir'],
                                             self.param_dict['base_data_dir'],
                                             self.param_dict['www_dir'],
                                             self.param_dict['www_derived_dir'],
                                             self.param_dict['www_base_dir'])
                                             
            # generate 1 or more HTML webpages
            if skip_flag:
                status_page_list = []
            else:
                status_page_list = page_generator.generate(self.param_dict['baseline_datetime'],
                                                           self.param_dict['max_age_days'],
                                                           self.param_dict['delta_min'])
            #end
                
            #
            # augment the existing dictionary list to add the filenames
            cam_list[index]['status_page_list'] = status_page_list    # formerly page_fnames_list
        #end
        return cam_list

    def print_summary(self, num_added, num_deleted_ext, num_deleted_age):
        self.logger.info("== SUMMARY ==")
        self.logger.info("CAMERAS:")
        cam_list = self.get_cam_list()
        for cam in cam_list:
            self.logger.info("%s" % cam['name'])
        #end
        self.logger.info("")
        self.logger.info("FILE PROCESSING:")
        self.logger.info("Files Deleted (wrong extension): %d" % num_deleted_ext)
        self.logger.info("Files Added: %d" % num_added)
        self.logger.info("")
        self.logger.info("DATASTORE:")
        self.logger.info("Num Entries deleted (age): %d" % num_deleted_age)
        all_rows = self.image_db.select_all()
        self.logger.info("Num Entries after processing: %d" % len(all_rows))
        
        return


    def write_breadcrumb(self):
        """
        write breadcrumb file for watchdog
        """
        f = open("pano-breadcrumb.txt","wt")
        now_string = str(datetime.datetime.now())
        f.write(now_string)
        f.close()
    
@click.command()
@click.argument('config')
@click.option('--loopcnt',default=-1,help='number of times to loop; -1 == forever')
@click.option('--droptable/--no-droptable', default=False,help='delete existing image database')
@click.option('--logfname', default='pano.log',help='specify \'stdout\' for sys.stdout')
@click.option('--loglevel',default='warning',help='valid values: \'debug\'|\'info\'|\'warning\'|\'error\'|\'critical\'')
def pano_main(config, loopcnt,droptable,loglevel,logfname):
    print("config file=%s" % config)
    print("loopcnt=%d" % loopcnt)
    mypano = Pano(config,droptable,loglevel,logfname)
    loop_flag = True
    loop_index=0
    while loop_flag:
        mypano.write_breadcrumb()
        (num_files_added, num_deleted_ext) = mypano.slurp_images(mypano.param_dict['skip_slurp'])
        num_deleted_age = mypano.cull_old_files(mypano.param_dict['skip_cull_old_files'])

        mypano.derive_media(mypano.param_dict['skip_derive_media'])
        
        cam_list = mypano.gen_camera_pages(mypano.param_dict['skip_gen_cam_pages'])
        mypano.logger.info("generated camera pages")

        index_fname = mypano.gen_index_page(cam_list)
        mypano.logger.info("updated index page (%s)" % index_fname)

        mypano.print_summary(num_files_added, num_deleted_ext, num_deleted_age)

        mypano.logger.info("cull & sleeping...%6.2f min" % mypano.param_dict['sleep_interval_min'])
        mypano.cull_and_sleep(mypano.param_dict['skip_cull_empty_dirs'])

        loop_index += 1
        if (loopcnt >= 0):
            loop_flag = loop_index < loopcnt
        else:
            loop_flag = True
        #end
    #end

if __name__=="__main__":
    pano_main()
    
