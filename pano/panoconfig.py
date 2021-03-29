import json
import os

DEFAULTS_JSON = """
{
    "base_data_dir" : "FTP",
    "baseline_datetime": "now",
    "database_fname" : "panodb.sqlite",
    "delta_min": 10,
    "derived_dir": "derived",
    "drop_table_flag": 0,
    "ffmpeg": "/usr/bin/ffmpeg",
    "log_dir": "./",
    "magick_convert": "/usr/bin/convert",
    "max_age_days": 14,
    "num_worker_threads": 1,
    "sleep_interval_min": 5,
    "www_dir": "www",
    "www_data_dir": "./FTP",
    "www_derived_dir": "./derived",

    "skip_derive_media": 0,
    "skip_slurp": 0,
    "skip_cull_old_files": 0,
    "skip_gen_cam_pages": 0,
    "skip_cull_empty_dirs": 0,
    
    "@camera_list (example)" : [
	{
            "name": "cam-00",
            "model": "amcrest-ip2m-842",
            "live_url": "rtsp://192.168.0.1",
	    "admin_url": "http://192.168.0.1",
            "description": "porch"
	},
	{
            "name": "cam-01",
            "model": "amcrest-ip3m-843",
            "live_url": "rtsp://192.168.0.1",
	    "admin_url": "http://192.168.0.1",
            "description": "porch"
	}
    ],
    "camera_list" : [],

    "watchdog_max_faults": 5,
    "watchdog_enable_reboot": 1,
    "watchdog_check_httpd": 1,
    "watchdog_check_ftpd" : 1,
    "watchdog_check_breadcrumb": 1
}
"""
def get_param_dict(config_fname, **config_override_args):
    config = load_base_config(config_fname)

    for key, value in config_override_args.items():
        if key in config.keys():
            config[key] = value
        #end
    #end

    #
    # convert file paths to absolute
    config['base_data_dir']     = os.path.abspath(config['base_data_dir'])
    config['database_fname']    = os.path.abspath(config['database_fname'])
    config['derived_dir']       = os.path.abspath(config['derived_dir'])
    config['log_dir']           = os.path.abspath(config['log_dir'])
    config['www_dir']           = os.path.abspath(config['www_dir'])

    #
    # the "www_" paths are meant to be relative to www_dir
    # config['www_data_dir']      = os.path.abspath(config['www_data_dir'])
    # config['www_derived_dir']   = os.path.abspath(config['www_derived_dir'])
    
    return config

def load_base_config(config_fname):
    """
        read user-specified config file, default config file,
        merge the two parameters

        returns:
        merged parameter dict
    """
    #
    # read config json, store in dict
    defaults_dict = json.loads(DEFAULTS_JSON)
    
    f = open(config_fname)
    user_param_dict = json.load(f)
    f.close()
    
    merged_dict = merge_dicts(defaults_dict, user_param_dict)
    
    #
    # normalize directory paths by making them absolute
    merged_dict['base_data_dir']  = os.path.normpath(merged_dict['base_data_dir'])
    merged_dict['database_fname'] = os.path.normpath(merged_dict['database_fname'])
    merged_dict['derived_dir']    = os.path.normpath(merged_dict['derived_dir'])
    merged_dict['www_dir']        = os.path.normpath(merged_dict['www_dir'])
    
    return merged_dict
    
def merge_dicts(defaults_dict, user_dict):
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
            del user_dict[k]
        else:
            final_val = default_val
        #end
        assert (final_val != "") , "parameter (%s) not assigned" % k
        merged_dict[k] = final_val
    #end

    if len(user_dict) > 0:
        #
        # can't use logging because its not yet configured!
        print( "Entries in user-specified JSON did not match entries in default JSON file")
        print(f"{user_dict}")
        assert False
    #endif

    # sanity checks
    assert len(merged_dict['camera_list']) > 0, "no cameras listed"
    assert len(merged_dict['base_data_dir']) > 0, "no base_data_dir specified"
    assert merged_dict['delta_min'] > 0, "delta min < 0"
    assert merged_dict['max_age_days'] > 0, "max_age_days < 0"
    
    return merged_dict
