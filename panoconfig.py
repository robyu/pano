import json

"""

"""
default_json_fname = "pano_defaults.json"

def get_param_dict(config_fname):
    """
        read user-specified config file, default config file,
        merge the two parameters

        returns:
        merged parameter dict
    """
    #
    # read config json, store in dict
    f = open(default_json_fname)
    defaults_dict = json.load(f)
    f.close()
    
    f = open(config_fname)
    user_param_dict = json.load(f)
    f.close()
    
    merged_dict = merge_dicts(defaults_dict, user_param_dict)
    
    #
    # normalize directory paths by making them absolute
    # merged_dict['base_data_dir']  = os.path.realpath(merged_dict['base_data_dir'])
    # merged_dict['database_fname'] = os.path.realpath(merged_dict['database_fname'])
    # merged_dict['derived_dir']    = os.path.realpath(merged_dict['derived_dir'])
    # merged_dict['www_dir']        = os.path.realpath(merged_dict['www_dir'])
    
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
