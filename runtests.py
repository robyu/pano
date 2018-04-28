
#!/usr/bin/env python

import sqlite3
import dirwalk
import unittest
import time
import subprocess
import os
import datastore
import pudb
import shutil
import webpage
import datetime
import tzlocal

"""
run all unit tests
python -m unittest runtests.py

run an individual test
python -m unittest testica.TestIca.test_smoketest   # works with #pu.db in code
"""

class TestPano(unittest.TestCase):
    test_data_dir = './testdata/FTP'

    def setUp(self):
        print("setup")
        subprocess.call(['./restore-testdata.sh'])

    def test_cull_files_by_ext(self):
        #pu.db
        num_deleted = dirwalk.cull_files_by_ext(root_dir=self.test_data_dir)
        print("num_deleted = %d" % num_deleted)
        self.assertTrue(num_deleted==290)
        
    def test_cull_files_by_age(self):
        baseline_time = time.strptime("26 feb 2018 00:00", "%d %b %Y %H:%M")
        baseline_time_epoch = time.mktime(baseline_time)
        num_deleted = dirwalk.cull_files_by_age(baseline_time_epoch=baseline_time_epoch, max_age_days=1.75,root_dir=self.test_data_dir)
        print("deleted %d files" % num_deleted)
        self.assertTrue(num_deleted==136)
        self.assertTrue(True)

    def test_cull_empty_dirs(self):
        dirwalk.cull_empty_dirs(self.test_data_dir)

        # FTP/cameras is an empty directory
        flag = os.path.exists(os.path.join(self.test_data_dir,'cameras'))
        print(flag)
        self.assertTrue(flag==False)

    def test_create_table(self):
        table_name = 'testtable'
        
        sqlite_file = './test_db.sqlite'
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS {tn};' \
                  .format(tn=table_name))
        c.execute('CREATE TABLE {tn} (id INTEGER)'.format(tn=table_name))
        c.execute("ALTER TABLE {tn} ADD COLUMN fname STRING".format(tn=table_name))
        c.execute("ALTER TABLE {tn} ADD COLUMN mediatype STRING".format(tn=table_name))
        c.execute("ALTER TABLE {tn} ADD COLUMN path STRING".format(tn=table_name))
        c.execute("ALTER TABLE {tn} ADD COLUMN mtime STRING".format(tn=table_name))
        c.execute("ALTER TABLE {tn} ADD COLUMN ctime STRING".format(tn=table_name))
        c.execute("ALTER TABLE {tn} ADD COLUMN processed_flag INTEGER".format(tn=table_name))
        
        conn.close()
        self.assertTrue(True)

    def test_create_table2(self):
        db = datastore.Datastore()
        db.close()
        self.assertTrue(True)

    def test_insert_row(self):
        db = datastore.Datastore()
        db.cursor.execute("INSERT INTO {tn} (fname, path, derived_fname) VALUES ('abcd', 'xyz', 'foo')".format(tn=db.tablename))
        db.cursor.execute("INSERT INTO {tn} (fname, path, derived_fname) VALUES ('efgh', '123', 'foo')".format(tn=db.tablename))
        #db.dbconn.commit()
        db.cursor.execute('SELECT * FROM {tn} WHERE fname like "%a%"'.format(tn=db.tablename))
        all_rows = db.cursor.fetchall()
        print(all_rows)
        print(len(all_rows))
        db.close()
        self.assertTrue(len(all_rows)==1)

    def test_walk_dir_and_store(self):
        #pu.db
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP')

        #
        # how many entries did we enter?
        cmd = "SELECT * FROM %s" % (db.tablename)
        db.cursor.execute(cmd)
        entries = db.cursor.fetchall()
        db.close()
        self.assertTrue(len(entries)==2642)

    def test_age_delta(self):
        #pu.db
        db = datastore.Datastore()

        #
        # get 'now'
        # db returns: [(u'1522438500',)]   
        cmd = "select strftime('%s','now','localtime')"
        db.cursor.execute(cmd)
        ret = db.cursor.fetchall()
        now_epoch = int(ret[0][0])

        #
        cmd  = "select strftime('%s','now','localtime','-2 days')"
        db.cursor.execute(cmd)
        ret = db.cursor.fetchall()
        prev_epoch = int(ret[0][0])

        diff_epoch = now_epoch - prev_epoch

        #
        # diff is equivalent to 2 days?
        diff_days = diff_epoch / (24.0 * 60.0 * 60.0)
        self.assertTrue(int(diff_days + 0.5)==2)
        
        db.close()

    def test_age_delta2(self):
        #pu.db
        db = datastore.Datastore()

        now = '2018-04-01T18:00:00.000'
        then = '2018-03-30T18:00:00.000'
        
        #
        # get 'now'
        # db returns: [(u'1522438500',)]   
        cmd = "select strftime('%s','{now}')".format(now=now)
        db.cursor.execute(cmd)
        ret = db.cursor.fetchall()
        now_epoch = int(ret[0][0])

        #
        cmd  = "select strftime('%s','{then}')".format(then=then)
        db.cursor.execute(cmd)
        ret = db.cursor.fetchall()
        prev_epoch = int(ret[0][0])

        diff_epoch = now_epoch - prev_epoch

        #
        # diff is equivalent to 2 days?
        diff_days = diff_epoch / (24.0 * 60.0 * 60.0)
        self.assertTrue(int(diff_days + 0.5)==2)
        
        db.close()

    def test_time_roundtrip(self):
        """
        iso8601 -> seconds -> iso8601

        select strftime('%s','2018-04-27 20:46:11','utc') -- convert time to UTC epoch time
        -- returns  1524887171
        select datetime('1524887171','unixepoch','localtime') -- interpret ddddd as unixepoch, convert to localtime, return yyyy-mm-dd hh:mm:ss
        -- result is 2018-04-27 20:46:11
        """
        pu.db
        time_string0 = '2018-04-01 18:00:00'
        db = datastore.Datastore()
        time_sec = db.iso8601_to_sec(time_string0)
        time_string = db.sec_to_iso8601(time_sec)
        #time_string = time_string.replace('T',' ')
        time_string = time_string.encode('utf8')    # convert from decode to plain
        self.assertTrue(time_string==time_string0)

    def test_time_roundtrip2(self):
        """
        seconds -> iso8601 -> seconds
        """
        pu.db
        db = datastore.Datastore()
        time_sec0 = 1524887171
        time_string = db.sec_to_iso8601(time_sec0)
        time_sec = db.iso8601_to_sec(time_string)

        self.assertTrue(time_sec==time_sec0)
        
        
    def test_select_by_age(self):
        #pu.db
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP')

        row_list = db.select_rows_by_age(baseline_time='2018-02-26', max_age_days=1)
        print(len(row_list))
        self.assertTrue(len(row_list)==1153)

        row_list = db.select_rows_by_age(baseline_time='2018-02-26', max_age_days=1.75)
        print(len(row_list))
        self.assertTrue(len(row_list)==123)
        
        db.close()

    def test_cull_files_by_age(self):
        #pu.db
        db = datastore.Datastore()
        num_entries = dirwalk.walk_dir_and_load_db(db, root_dir='testdata/FTP')
        
        num_deleted = dirwalk.cull_files_by_age(db,
                                                root_dir='testdata/FTP',
                                                baseline_time='2018-02-26',
                                                max_age_days=1)
        row_list = db.select_all()
        
        self.assertTrue(num_deleted==1153)
        self.assertTrue(len(row_list) + num_deleted==num_entries)
        db.close()

    def test_update_row(self):
        #pu.db
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP')
        row_list = db.select_all()
        id = row_list[-1].d['id']
        db.update_row(id, 'derived_fname', 'foo')

        row = db.select_by_id(id)
        self.assertTrue(row.d['id'] == id)
        self.assertTrue(row.d['derived_fname']=='foo')
        db.close()


    def test_make_derived_files(self):
        #pu.db
        try:
            shutil.rmtree(dirwalk.DERIVED_DIR)
        except:
            pass
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP')
        num_deleted = dirwalk.cull_files_by_age(db,
                                                root_dir='testdata/FTP',
                                                baseline_time='2018-02-26',
                                                max_age_days=0.25)
        dirwalk.make_derived_files(db, root_dir='testdata/FTP')
        db.close()

    def test_string_to_sec(self):
        db = datastore.Datastore()
        start_sec = db.iso8601_to_sec('2018-03-27T03:03:00')
        print("%d" % start_sec)
        
        self.assertTrue(start_sec==1522094580)

    def test_time_iterate(self):
        db = datastore.Datastore()
        incr_sec = 60 * 10   # 10 minutes
        
        
        start_sec = db.iso8601_to_sec('2018-03-27T03:03:00')
        print("%d" % start_sec)
        max_age_sec = start_sec - int(24 * 60 * 60 * 0.5)
        

        upper_time_sec = start_sec
        lower_time_sec = start_sec - incr_sec
        
        while lower_time_sec > max_age_sec:
            diff_sec = upper_time_sec - lower_time_sec
            diff_min = diff_sec / 60.0
            print("| %15d .. %15d | diff = %f min" % (upper_time_sec, lower_time_sec, diff_min))

            upper_time_sec = lower_time_sec
            lower_time_sec = upper_time_sec - incr_sec
        
        self.assertTrue(True)

    def test_select_by_time(self):
        pu.db
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP')
        delta_sec = 60 * 10   # 10 minutes
        upper_time_sec = db.iso8601_to_sec('2018-02-25T19:14:22')
        lower_time_sec = upper_time_sec - delta_sec

        row_list = db.select_by_time_cam_media('b0',upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_IMAGE)
        self.assertTrue(len(row_list)==6)
        
    def test_gen_webpage(self):
        pu.db
        start_time = '2018-02-25T19:14:22'
        delta_min = 10

        #
        # populate db and get rows corresponding to time interval
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        num_deleted = dirwalk.cull_files_by_age(db,
                                                root_dir='testdata/FTP-culled',
                                                baseline_time='2018-02-26',
                                                max_age_days=0.25)
        dirwalk.make_derived_files(db, root_dir='testdata/FTP-culled')
        delta_sec = 60 * delta_min   # 10 minutes
        upper_time_sec = db.iso8601_to_sec(start_time)
        lower_time_sec = upper_time_sec - delta_sec
        row_image_list = db.select_by_time_cam_media('b0',upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_IMAGE)
        row_video_list = db.select_by_time_cam_media('b0',upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_VIDEO)
        db.close()
        self.assertTrue(len(row_image_list)==6)
        self.assertTrue(len(row_video_list)==2)

        fname_webpage = 'www/test_b0.html'
        cam_webpage = webpage.Webpage(fname_webpage, './testdata/FTP-culled')
        cam_webpage.write_header()

        row_html = cam_webpage.make_html_image_list(row_image_list)
        video_html = cam_webpage.make_html_video_list(row_video_list)
        datetime_upper = datetime.datetime.fromtimestamp(upper_time_sec).strftime('%I:%M:%S')
        datetime_lower = datetime.datetime.fromtimestamp(lower_time_sec).strftime('%I:%M:%S')
        cam_webpage.write_row(row_html, video_html, datetime_upper, datetime_lower)
        cam_webpage.write_row(row_html, video_html, datetime_upper, datetime_lower)
        cam_webpage.write_row(row_html, video_html, datetime_upper, datetime_lower)
        
        cam_webpage.close()
        
        self.assertTrue(os.path.exists(fname_webpage))

    def OLDtest_gen_webpage_1day(self):
        pu.db
        start_time = '2018-02-25T19:14:22'
        delta_min = 10

        #
        # populate db and get rows corresponding to time interval
        testdata_dir  = 'testdata/FTP'
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, testdata_dir)
        num_deleted = dirwalk.cull_files_by_age(db,
                                                root_dir=testdata_dir,
                                                baseline_time='2018-02-26',
                                                max_age_days=1)
        dirwalk.make_derived_files(db, testdata_dir)
        delta_sec = 60 * delta_min   # 10 minutes
        upper_time_sec = db.iso8601_to_sec(start_time)
        lower_time_sec = upper_time_sec - delta_sec
        row_image_list = db.select_by_time_cam_media('b0',upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_IMAGE)
        row_video_list = db.select_by_time_cam_media('b0',upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_VIDEO)
        db.close()
        print("num image rows: %d" % len(row_image_list))
        print("num video rows: %d" % len(row_video_list))

        fname_webpage = 'www/test_b0.html'
        cam_webpage = webpage.Webpage(fname_webpage, testdata_dir)
        cam_webpage.write_header()

        row_html = cam_webpage.make_html_image_list(row_image_list)
        video_html = cam_webpage.make_html_video_list(row_video_list)
        cam_webpage.write_row(row_html, video_html)
        cam_webpage.write_row(row_html, video_html)
        cam_webpage.write_row(row_html, video_html)
        
        cam_webpage.close()
        
        self.assertTrue(os.path.exists(fname_webpage))
                        
        
if __name__ == '__main__':
    unittest.main()
    
