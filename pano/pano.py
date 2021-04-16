import datastore
import dirwalk
import os
import campage
import derived
import indexpage
import time
import panoconfig
import datetime
import logging
import logging.handlers
import sys
import dtutils
import uuid
import argparse

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
    
    def __init__(self, config_fname, loglevel='warning', logfname='stdout', **config_override_args):
        """
        kwargs lets you override values in the config file.
        e.g.
        you can specify 
            Pano.init("config.json", num_worker_threads=1)
        to override the num_worker_threads parameter in config.json

        see panoconfig.py for the canonical config JSON
        """
        print("Pano: reading config file (%s)" % config_fname)

        self.param_dict = panoconfig.get_param_dict(config_fname, **config_override_args)

        
        self.logger = self.configure_logging(loglevel, logfname)
        self.verify_paths()

        # DO NOT generate symlinks, because the docker 
        # environment uses different symlinks
        #self.generate_www_sym_links()
        
        if self.param_dict['drop_table_flag']==0:
            drop_table_flag=False
        else:
            logging.info("drop existing table")
            drop_table_flag=True
        #end 
        self.image_db = datastore.Datastore(self.param_dict['database_fname'],
                                            drop_table_flag=drop_table_flag)

        self.print_baseline_time_info()
            
        cam_list = self.get_cam_list()
        logging.info("")
        logging.info("REGISTERED CAMERAS:")
        logging.info("===================")
        for cam in cam_list:
            logging.info(cam['name'])
        #end

    def verify_paths(self):
        full_www_data_dir = os.path.normpath(os.path.join(self.param_dict['www_dir'], self.param_dict['www_data_dir']))
        full_www_derived_dir = os.path.normpath(os.path.join(self.param_dict['www_dir'], self.param_dict['www_derived_dir']))
        logging.info("")
        logging.info("VERIFY CONFIG PATHS")
        logging.info("===================")
        logging.info(f"base_data_dir:   {self.param_dict['base_data_dir']} ")
        logging.info(f"derived_dir:     {self.param_dict['derived_dir']}. ")
        logging.info(f"www_dir:         {self.param_dict['www_dir']} ")
        logging.info(f"www_dir/css:     {self.param_dict['base_data_dir']}/css ")
        logging.info(f"www_dir/fonts:   {self.param_dict['base_data_dir']}/fonts ")
        logging.info(f"www_dir/js:      {self.param_dict['base_data_dir']}/js ")
        logging.info(f"www_dir/mryuck.png:    {self.param_dict['base_data_dir']}/mryuck.png ")
        logging.info(f"www_data_dir (full):    {full_www_data_dir}")
        logging.info(f"www_derived_dir (full): {full_www_derived_dir}")

        #
        # check base and derived directories
        assert os.path.exists(self.param_dict['base_data_dir'])
        assert os.path.exists(self.param_dict['derived_dir'])

        # check www and subdirs
        assert os.path.exists(self.param_dict['www_dir'])
        assert os.path.exists(os.path.join(self.param_dict['www_dir'], 'css'))
        assert os.path.exists(os.path.join(self.param_dict['www_dir'], 'fonts'))
        assert os.path.exists(os.path.join(self.param_dict['www_dir'], 'js'))
        assert os.path.exists(os.path.join(self.param_dict['www_dir'], 'mryuck.png'))

        # www/FTP must be a link
        assert os.path.isabs(self.param_dict['www_data_dir'])==False
        assert os.path.islink(full_www_data_dir)

        # www/derived must be a link
        assert os.path.isabs(self.param_dict['www_derived_dir'])==False
        assert os.path.islink(full_www_derived_dir)
        

    def print_baseline_time_info(self):
        """
        write some stuff about the configured baseline time and duration
        """
        logging.info("")
        logging.info("BASELINE TIME INFO")
        logging.info("==================")
        baseline_datetime = self.param_dict['baseline_datetime']
        max_age_days = self.param_dict['max_age_days']
        logging.info(f"baseline_datetime = {baseline_datetime}")
        logging.info(f"max_age_days = {max_age_days}")
        baseline_sec = self.image_db.iso8601_to_sec(baseline_datetime)
        logging.info(f"baseline_datetime = {baseline_sec} sec")
        logging.info(f"baseline_datetime = {dtutils.sec_to_str(baseline_sec)} (roundtrip conversion)")
        max_age_sec = self.param_dict['max_age_days'] * 24.0 * 60.0 * 60.0
        oldest_sec = baseline_sec - max_age_sec
        oldest_datetime = dtutils.sec_to_str(oldest_sec)
        logging.info(f"scanning media from {oldest_datetime} .. {baseline_datetime}")

        #end
        return
        
    def configure_logging(self, loglevel,logfname):
        """
        agh, python logging is awful

        loglevels are defined by the logging module: DEBUG, INFO, WARNING, ERROR
        
        logfname: specify a filename 
                  specifying 'stdout' or None logs to sys.stdout
        """
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        if logfname=='stdout' or logfname==None:
            print(f"logging to stdout")
            logging.basicConfig(stream=sys.stdout,
                                level=numeric_level,
                                format='%(asctime)s %(levelname)-8s %(message)s')

        elif len(logfname) > 0:
            assert os.path.exists(self.param_dict['log_dir']), f"log directory does not exist: {self.param_dict['log_dir']}  "
            log_dest = os.path.join(self.param_dict['log_dir'], logfname)
            log_dest = os.path.normpath(log_dest)


            print(f"logging to {log_dest}")

            logger = logging.getLogger(log_dest)
            logHandler = logging.handlers.RotatingFileHandler(log_dest, maxBytes=5e+8, backupCount=6)

            logging.basicConfig(
                                level=numeric_level,
                                format='%(asctime)s %(levelname)-8s %(message)s',
                                handlers=[logHandler])
        else:
            assert False, "invalid logfname"
        #end
        
        
        logging.debug(   "DEBUG     logging enabled")
        logging.info(    "INFO      logging enabled")
        logging.warning( "WARNING   logging enabled")
        logging.error(   "ERROR     logging enabled")
        logging.critical("CRITICAL logging enabled")
        
    #@timeit.timeit
    def NOTINUSEgenerate_www_sym_links(self):
        """
        generate links in www directory to data directories
        """
        data_dir = self.param_dict['base_data_dir']
        www_data_dir = os.path.normpath(os.path.join(self.param_dict['www_dir'],
                                                     self.param_dict['www_data_dir']))
        if os.path.islink(www_data_dir) and os.path.realpath(www_data_dir) == data_dir:
            pass
        else:
            unique = uuid.uuid1()
            os.rename(www_data_dir, f"{www_data_dir}-{unique}")
            os.symlink(data_dir, www_data_dir)
        #end

        derived_dir = self.param_dict['derived_dir']
        www_derived_dir = os.path.normpath(os.path.join(self.param_dict['www_dir'],
                                                        self.param_dict['www_derived_dir']))
        if os.path.islink(www_derived_dir) and os.path.realpath(www_derived_dir)==derived_dir:
            pass
        else:
            unique = uuid.uuid1()
            os.rename(www_derived_dir, f"{www_derived_dir}-{unique}")
            os.symlink(derived_dir, www_derived_dir)
        #end

    #@timeit.timeit
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
        logging.info("** slurp images")

        if skip_flag:
            logging.debug("skipping slurp")
            return (total_files_added, total_files_deleted)
        #endif
        
        base_data_dir = self.param_dict['base_data_dir']
        cam_list = self.get_cam_list()
        for cam in cam_list:
            cam_name_model_list = [ (cam['name'], cam['model'] ) ]
            cam_dir = os.path.join(base_data_dir, cam['name']) # "testdata/FTP-culled/b0"
            logging.debug("*** processing camera dir %s" % cam_dir)
            num_deleted = dirwalk.cull_files_by_ext(base_data_dir=cam_dir)
            num_added = dirwalk.walk_dir_and_load_db(self.image_db,
                                                     base_data_dir,
                                                     cam_name_model_list)
            total_files_added += num_added
            total_files_deleted += num_deleted
        #end
        return (total_files_added, total_files_deleted)

    #@timeit.timeit
    def cull_empty_dirs(self, skip_flag=False):
        """
        """
        logging.info("delete empty dirs")

        if skip_flag:
            logging.info("skipping cull_empty_dirs")
            return
        #endif

        # delete empty dirs in the data directory, e.g. FTP/cam00
        base_data_dir = self.param_dict['base_data_dir']
        derived_dir = self.param_dict['derived_dir']
        cam_list = self.get_cam_list()
        for cam in cam_list:
            cam_dir = os.path.join(base_data_dir, cam['name']) # "testdata/FTP-culled/b0"
            logging.debug("cull empty dirs %s" % cam_dir)
            dirwalk.cull_empty_dirs(cam_dir)

            cam_dir = os.path.join(derived_dir, cam['name'])
            logging.debug("cull empty dirs %s" % cam_dir)
            dirwalk.cull_empty_dirs(cam_dir)
        #end

        return

    def cull(self, skip_cull_flag=False):
        cull_start = time.time()
        self.cull_empty_dirs(skip_cull_flag)
        cull_stop = time.time()

        return

    def sleep(self):
        sleep_sec = self.param_dict['sleep_interval_min'] * 60.0
        assert sleep_sec >= 0.0


        while sleep_sec > 0:
            sleep_interval_sec = min(20, sleep_sec)
            sleep_sec = sleep_sec - sleep_interval_sec
            logging.info(f"sleep for {sleep_interval_sec} sec ({sleep_sec} sec remaining)")
            time.sleep(sleep_interval_sec)
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
    
    #@timeit.timeit
    def gen_index_page(self, cam_list):
        """
        IN:
        cam_list: list of per-camera dict objects
        """
        logging.info("** generate index page")
        assert len(cam_list) > 0, "you gotta run gen_camera_pages first"
        
        index_page = indexpage.IndexPage(self.image_db,
                                         self.param_dict['www_dir'],
                                         self.param_dict['derived_dir'],
                                         self.param_dict['www_derived_dir'])
        index_fname = index_page.make_index(cam_list)
        return index_fname

    #@timeit.timeit
    def cull_old_files(self, skip_flag):
        """
        search through datastore, find old entries and delete entries
        and corresponding media files

        returns:
        num entries deleted
        """
        logging.info("** cull files by age")
        if skip_flag:
            logging.info(f"skip_flag={skip_flag}, skipping cull_old_files")
            num_deleted = 0
        else:
            logging.info("cull_old_files")
            num_deleted = dirwalk.cull_files_by_age(self.image_db,
                                                    derived_dir = self.param_dict['derived_dir'],
                                                    baseline_time = self.param_dict['baseline_datetime'],
                                                    keep_days = self.param_dict['max_age_days'])
        #END
        return num_deleted
    
    #@timeit.timeit
    def derive_media(self, skip_flag=False):
        """
        for each camera listed in the json file, 
        generate derivative media files (thumbnails, etc)

        returns:
        none
        """
        logging.info("** make derived media")
        if skip_flag:
            return
        #end
        
        cam_list = self.get_cam_list()

        for index in range(len(cam_list)):
            cam_name = cam_list[index]['name']

            derived.make_derived_files(self.image_db,
                                       cam_name,
                                       num_workers = self.param_dict['num_worker_threads'],
                                       derived_dir = self.param_dict['derived_dir'],
                                       cmd_ffmpeg = self.param_dict['ffmpeg'],
                                       cmd_magick_convert = self.param_dict['magick_convert'])

        #end
        return

    #@timeit.timeit
    def gen_camera_pages(self, skip_flag=False):
        """
        for each camera listed in the json file, 
        generate a webpage 

        returns:
        list of dictionary elements, where each element is
        the camera-info list (see get_cam_list) plus an extra entry, "status_page_list"
        listing the web pages
        """
        logging.info("** generate camera webpages")

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
                                             self.param_dict['www_data_dir'])
                                             
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
        logging.warning("== SUMMARY ==")
        logging.warning("CAMERAS:")
        cam_list = self.get_cam_list()
        for cam in cam_list:
            logging.warning("%s" % cam['name'])
        #end
        logging.warning("")
        logging.warning("FILE PROCESSING SUMMARY:")
        logging.warning("Files Deleted (wrong extension): %d" % num_deleted_ext)
        logging.warning("Files Added: %d" % num_added)
        logging.warning("")
        logging.warning("DATASTORE:")
        logging.warning("Num Entries deleted (age): %d" % num_deleted_age)
        all_rows = self.image_db.select_all()
        logging.warning("Num Entries after processing: %d" % len(all_rows))
        
        return


    def write_breadcrumb(self):
        """
        write breadcrumb file for watchdog
        """
        f = open("pano-breadcrumb.txt","wt")
        now_string = str(datetime.datetime.now())
        f.write(now_string)
        f.close()

    def loop(self, maxloops=-1):
        loop_flag = True
        loop_index=0
        while True:
            self.write_breadcrumb()
            (num_files_added, num_deleted_ext) = self.slurp_images(self.param_dict['skip_slurp'])
            num_deleted_age = self.cull_old_files(self.param_dict['skip_cull_old_files'])

            self.derive_media(self.param_dict['skip_derive_media'])

            cam_list = self.gen_camera_pages(self.param_dict['skip_gen_cam_pages'])
            logging.info("generated camera pages")

            index_fname = self.gen_index_page(cam_list)
            logging.info("updated index page (%s)" % index_fname)

            self.print_summary(num_files_added, num_deleted_ext, num_deleted_age)

            logging.info("cull")
            self.cull(self.param_dict['skip_cull_empty_dirs'])
            loop_index += 1

            if (loop_index >= maxloops) and (maxloops > 0):
                break
            #end
            self.sleep()

        #end

    def clear_derived(self):
        rows = self.image_db.select_all()
        count=0
        for row in rows:
            if row.d['derive_failed']==1:
                self.image_db.update_row(row.d['id'],'derive_failed',0)
                count += 1
            #end
        #end
        logging.info(f"cleared derive_failed in {count} entries")
        
        

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loopcnt",   type=int,  default=-1,help="number of times to loop; -1 == forever")
    parser.add_argument("--droptable",   dest='droptable', action="store_true",  help="delete existing image db")
    parser.add_argument("--nodroptable", dest='droptable', action="store_false", help="delete existing image db")
    parser.add_argument("--logfname", type=str, default="pano.log", help="specify 'stdout' for sys.stdout")
    parser.add_argument("--loglevel", type=str, default="warning",
                        help="valid values: 'debug', 'info', 'warning', 'error', 'critical'")
    parser.add_argument("--clearderived", dest="clearderived", action="store_true", help="clear all derive_failed entries in db")
    parser.add_argument("config", type=str, help="filename of the JSON config file")
    args = parser.parse_args()
    return args

if __name__=="__main__":
    args = parse_args()
    
    print("config file=%s" % args.config)
    print("loopcnt=%d" % args.loopcnt)
    if args.droptable==True:
        droptable_flag = 1
    else:
        droptable_flag = 0
    #end
    mypano = Pano(args.config, args.loglevel, args. logfname, droptable=droptable_flag)

    if args.clearderived:
        mypano.clear_derived()
    
    mypano.loop(args.loopcnt)

    
