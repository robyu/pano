import datastore

class ip2m_842:
    def __init__(self):
        pass

    def parse(self, dir_path, fname):
        """
        e.g.
        cam_dir = './testdata/FTP/b1'
        dir_path = ./testdata/FTP/b1/AMC002A3_K2G7HH/2018-02-25/001/jpg/18/53
        fname = 29[M][0@0][0].jpg
        """
        dir_element_list = dir_path.split('/')

        # at this point, dir_element_list contains:
        # 
        # >>> dir_element_list
        # ['.', 'FTP', 'cam-00', 'AMC0028V_795UUB', '2021-03-06', '001', 'jpg', '12', '57']
        # >>> fname
        # '18[M][0@0][0].jpg'
        # 
        # or
        # 
        # >>> dir_element_list
        # ['.', 'FTP', 'cam-00', 'AMC0028V_795UUB', '2021-03-06', '001', 'dav', '10']
        # >>> fname
        # '10.27.32-10.28.00[M][0@0][0].dav'        
        if dir_element_list[-3] == 'jpg' and fname[-3:] == 'jpg':
            media_type, ctime = self.parse_info_amcrest_jpg(dir_element_list, fname)
        elif dir_element_list[-2] == 'dav' and fname[-3:] == 'dav':
            media_type, ctime = self.parse_info_amcrest_dav(dir_element_list, fname)
        else:
            #print('dont know how to handle %s %s' % (row.d['path'], row.d['fname']))
            media_type = datastore.MEDIA_UNKNOWN
            ctime = ''
        # end

        return media_type, ctime

    def parse_info_amcrest_jpg(self, dir_element_list, fname):
        # >>> dir_element_list
        # ['.', 'FTP', 'cam-00', 'AMC0028V_795UUB', '2021-03-06', '001', 'jpg', '12', '57']
        # >>> fname
        # '18[M][0@0][0].jpg'
        assert dir_element_list[-3] == 'jpg'

        media_type = datastore.MEDIA_JPG

        date = dir_element_list[-5]
        hour = int(dir_element_list[-2])
        minute = int(dir_element_list[-1])
        sec = int(fname[0:2])
        ctime = '%sT%02d:%02d:%02d' % (date, hour, minute, sec)
        return media_type, ctime

    def parse_info_amcrest_dav(self, dir_element_list, fname):
        # >>> dir_element_list
        # ['.', 'FTP', 'cam-00', 'AMC0028V_795UUB', '2021-03-06', '001', 'dav', '12']
        # >>> fname
        # '12.23.10-12.23.10[M][0@0][0].dav'

        assert dir_element_list[-2]=='dav'

        media_type = datastore.MEDIA_DAV
        date = dir_element_list[-4]
        hour = int(fname[0:2])
        minute = int(fname[3:5])
        sec = int(fname[6:8])
        ctime = '%sT%02d:%02d:%02d' % (date, hour, minute, sec)
        return media_type, ctime

class ip3m_943:
    def __init__(self):
        pass

    def parse(self, dir_path, fname):
        """
        """
        dir_element_list = dir_path.split('/')

        # FTP/cam-07/AMC01848_F01N44/2021-03-06/10hour/jpg
        # 10.14.26[M][0@0][0].jpg

        # or
        # FTP/cam-07/AMC01848_F01N44/2021-03-06/10hour/mp4
        # 10.22.28-10.22.55[M][0@0][0].mp4
        if dir_element_list[-1] == 'jpg' and fname[-3:] == 'jpg':
            media_type, ctime = self.parse_info_amcrest_jpg(dir_element_list, fname)
        elif dir_element_list[-1] == 'mp4' and fname[-3:] == 'mp4':
            media_type, ctime = self.parse_info_amcrest_mp4(dir_element_list, fname)
        else:
            #print('dont know how to handle %s %s' % (row.d['path'], row.d['fname']))
            media_type = datastore.MEDIA_UNKNOWN
            ctime = ''
        # end

        return media_type, ctime

    def parse_info_amcrest_jpg(self, dir_element_list, fname):
        """
        FTP/cam-07/AMC0184D_F01N44/2021-03-12/08hour/jpg:
        08.37.42[M][0@0][0].jpg
        """
        assert dir_element_list[-1] == 'jpg'

        media_type = datastore.MEDIA_JPG

        date = dir_element_list[-3]
        hour = int(fname[0:2])
        minute = int(fname[3:5])
        sec = int(fname[6:8])
        ctime = '%sT%02d:%02d:%02d' % (date, hour, minute, sec)
        return media_type, ctime

    def parse_info_amcrest_mp4(self, dir_element_list, fname):
        """
        FTP/cam-07/AMC0184D_F01N44/2021-03-12/08hour/mp4:
        08.37.36-08.37.38[M][0@0][0].mp4
        """

        assert dir_element_list[-1]=='mp4'
        media_type = datastore.MEDIA_MP4

        date = dir_element_list[-3]
        hour = int(fname[0:2])
        minute = int(fname[3:5])
        sec = int(fname[6:8])
        ctime = '%sT%02d:%02d:%02d' % (date, hour, minute, sec)
        return media_type, ctime
    
def create(cam_model):
    if cam_model == 'amcrest-ip2m-842':
        parser = ip2m_842()
    elif cam_model == 'amcrest-ip3m-943':
        parser = ip3m_943()
    else:
        parser = None
    #end

    return parser
