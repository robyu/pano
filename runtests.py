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
import json
import pano
import derived
import glob

"""
run all unit tests
python -m unittest runtests.py

run an individual test
python -m unittest testica.TestIca.test_smoketest   # works with #pu.db in code
"""

class TestPano(unittest.TestCase):
    test_data_dir = './testdata/FTP-culled'
    derived_dir = './derived'

    def setUp(self):
        print("setup")
        subprocess.call(['./restore-testdata.sh'])

        fname_list = glob.glob("www/*.html")
        for fname in fname_list:
            os.remove(fname)

    def test_cull_files_by_ext(self):
        #pu.db
        num_deleted = dirwalk.cull_files_by_ext(base_data_dir=self.test_data_dir)
        print("num_deleted = %d" % num_deleted)
        self.assertTrue(num_deleted==290)
        
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
        db = datastore.Datastore(drop_table_flag=True)
        db.close()
        self.assertTrue(True)

    def test_insert_row(self):
        db = datastore.Datastore(drop_table_flag=True)
        db.cursor.execute("INSERT INTO {tn} (fname, path, derived_fname) VALUES ('abcd', 'xyz', 'foo')".format(tn=db.tablename))
        db.cursor.execute("INSERT INTO {tn} (fname, path, derived_fname) VALUES ('efgh', '123', 'foo')".format(tn=db.tablename))
        #db.dbconn.commit()
        db.cursor.execute('SELECT * FROM {tn} WHERE fname like "%a%"'.format(tn=db.tablename))
        all_rows = db.cursor.fetchall()
        print(all_rows)
        print(len(all_rows))
        db.close()
        self.assertTrue(len(all_rows)==1)

    def test_insert_same_row(self):
        db = datastore.Datastore(drop_table_flag=True)
        db.cursor.execute("INSERT INTO {tn} (fname, path, derived_fname) VALUES ('abcd', 'xyz', 'foo')".format(tn=db.tablename))
        db.cursor.execute("INSERT INTO {tn} (fname, path, derived_fname) VALUES ('1234', '567', 'bar')".format(tn=db.tablename))

        # this row should be ignored because fname and path match previous row
        db.cursor.execute("INSERT INTO {tn} (fname, path, derived_fname) VALUES ('abcd', 'xyz', 'foo')".format(tn=db.tablename))

        all_rows = db.select_all()
        print(all_rows)
        print(len(all_rows))
        db.close()
        self.assertTrue(len(all_rows)==2)
        
        
    def test_walk_dir_and_load(self):
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        num_added = dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        db.close()
        self.assertTrue(num_added==2642)

    def test_walk_dir_and_load_twice(self):
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        num_added = dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        db.close()
        self.assertTrue(num_added==2642)

        #
        # 2nd time around, do not drop table
        # verify that we do not add redundant entries to table
        db = datastore.Datastore(drop_table_flag=False)
        num_added = dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        db.close()
        self.assertTrue(num_added==0)
        

    def test_age_delta(self):
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)

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
        db = datastore.Datastore(drop_table_flag=True)

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
        #pu.db
        time_string0 = '2018-04-01 18:00:00'
        db = datastore.Datastore(drop_table_flag=True)
        time_sec = db.iso8601_to_sec(time_string0)
        time_string = db.sec_to_iso8601(time_sec)
        #time_string = time_string.replace('T',' ')
        time_string = time_string.encode('utf8')    # convert from decode to plain
        self.assertTrue(time_string==time_string0)

    def test_time_roundtrip2(self):
        """
        seconds -> iso8601 -> seconds
        """
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        time_sec0 = 1524887171
        time_string = db.sec_to_iso8601(time_sec0) # 2018-04-27 20:46:11
        time_sec = db.iso8601_to_sec(time_string)

        self.assertTrue(time_sec==time_sec0)

    def test_select_by_age(self):
        """
        for FTP-culled,
        select * from pano where ctime_unix between 1519614800 and 1519614862
        yields 4 rows

        where 1519614862==2018-02-25T19:14:22
        """
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')

        row_list = db.select_by_age_range(baseline_time='2018-02-25T19:14:22', max_age_days=0.0007)  # ~ 1 min
        print(len(row_list))
        self.assertTrue(len(row_list)==4)

        row_list = db.select_by_age_range(baseline_time='2018-02-26', max_age_days=0.25)
        print(len(row_list))
        self.assertTrue(len(row_list)==27)

        row_list = db.select_by_age_range(baseline_time='2018-02-26', max_age_days=0.33)
        print(len(row_list))
        self.assertTrue(len(row_list)==423)

        db.close()

    def test_cull_files_by_age(self):
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        num_entries = dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        
        row_list = db.select_all()
        num_before = len(row_list)
        num_deleted = dirwalk.cull_files_by_age(db,
                                                baseline_time='2018-02-26',
                                                max_age_days=.33)
        row_list = db.select_all()
        num_after=len(row_list)

        print("num before = %d" % num_before)
        print("num deleted = %d" % num_deleted)
        print("num after = %d" % num_after)
        
        self.assertTrue(num_deleted==2219)
        self.assertTrue(num_after + num_deleted==num_before)
        db.close()

    def test_update_row(self):
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        row_list = db.select_all()
        id = row_list[-1].d['id']
        db.update_row(id, 'derived_fname', 'foo')

        row = db.select_by_id(id)
        self.assertTrue(row.d['id'] == id)
        self.assertTrue(row.d['derived_fname']=='foo')
        db.close()


    def test_make_derived_files_multi_even(self):
        #pu.db
        try:
            shutil.rmtree(self.derived_dir)
        except:
            pass
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        num_deleted = dirwalk.cull_files_by_age(db,
                                                baseline_time='2018-02-26',
                                                max_age_days=0.33)
        count_success, count_failed = derived.make_derived_files(db,
                                                                 derived_dir=self.derived_dir,
                                                                 num_workers = 4)
        self.assertTrue (count_success==418)
        self.assertTrue(count_failed==5)
        db.close()

    def test_make_derived_files_multi_odd(self):
        #pu.db
        try:
            shutil.rmtree(self.derived_dir)
        except:
            pass
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        num_deleted = dirwalk.cull_files_by_age(db,
                                                baseline_time='2018-02-26',
                                                max_age_days=0.33)
        count_success, count_failed = derived.make_derived_files(db,
                                                                 derived_dir=self.derived_dir,
                                                                 num_workers = 3)
        self.assertTrue (count_success==418)
        self.assertTrue(count_failed==5)
        db.close()
        
    def test_string_to_sec(self):
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        timestring = '2018-02-25T19:14:22'
        start_sec = db.iso8601_to_sec(timestring)
        print("%d" % start_sec)
        
        self.assertTrue(start_sec==1519614862)

    def test_time_iterate(self):
        db = datastore.Datastore(drop_table_flag=True)
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
        #pu.db
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        delta_sec = 60 * 10   # 10 minutes
        upper_time_sec = db.iso8601_to_sec('2018-02-25T19:14:22')
        lower_time_sec = upper_time_sec - delta_sec

        row_list = db.select_by_time_cam_media('b0',upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_IMAGE)
        self.assertTrue(len(row_list)==6)
        
    def test_gen_webpage(self):
        #pu.db
        start_time = '2018-02-25T19:14:22'
        delta_min = 10
        camera_name = 'b0'

        #
        # populate db and get rows corresponding to time interval
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP-culled')
        num_deleted = dirwalk.cull_files_by_age(db,
                                                baseline_time='2018-02-26',
                                                max_age_days=0.25)
        derived.make_derived_files(db)
        delta_sec = 60 * delta_min   # 10 minutes
        upper_time_sec = db.iso8601_to_sec(start_time)
        lower_time_sec = upper_time_sec - delta_sec
        row_image_list = db.select_by_time_cam_media(camera_name,upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_IMAGE)
        row_video_list = db.select_by_time_cam_media(camera_name,upper_time_sec, lower_time_sec,mediatype=datastore.MEDIA_VIDEO)
        self.assertTrue(len(row_image_list)==6)
        self.assertTrue(len(row_video_list)==2)

        fname_webpage = 'www/test_b0.html'
        cam_webpage = webpage.Webpage(fname_webpage, camera_name, self.derived_dir,self.test_data_dir)
        cam_webpage.write_header()

        row_html = cam_webpage.make_html_image_list(row_image_list)
        video_html = cam_webpage.make_html_video_list(row_video_list)
        upper_datetime = db.sec_to_iso8601(upper_time_sec)
        lower_datetime = db.sec_to_iso8601(lower_time_sec)
        cam_webpage.write_row(row_html, video_html, upper_datetime, lower_datetime)
        cam_webpage.write_row(row_html, video_html, upper_datetime, lower_datetime)
        cam_webpage.write_row(row_html, video_html, upper_datetime, lower_datetime)
        
        cam_webpage.close()
        db.close()
        
        self.assertTrue(os.path.exists(fname_webpage))


    def test_gen_webpage2(self):
        #pu.db
        start_datetime = '2018-02-25T19:14:22'
        delta_min = 10

        #
        # populate db and get rows corresponding to time interval
        testdata_dir  = 'testdata/FTP-culled'
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, testdata_dir)
        num_deleted = dirwalk.cull_files_by_age(db,
                                                baseline_time='2018-02-26',
                                                max_age_days=0.33)
        derived.make_derived_files(db)
        fname_webpage = 'www/test_b0.html'
        camera_name = 'b0'

        try:
            os.remove(fname_webpage)
        except OSError:
            pass

        cam_webpage = webpage.Webpage(fname_webpage, camera_name, self.derived_dir, testdata_dir)
        cam_webpage.make_webpage(start_datetime, 1, delta_min, db)

        self.assertTrue(os.path.exists(fname_webpage))

    def test_read_json(self):
        #pu.db
        f = open('testdata2/test_pano_init.json','rt')
        d = json.load(f)
        print(d)
        self.assertTrue(d['camera_list'][0]['name']==u'b0')
        self.assertTrue(len(d['camera_list'])==2)
        self.assertTrue(d['max_age_days']==0.25)

    def test_pano_init(self):
        #pu.db
        mypano = pano.Pano("testdata2/test_pano_init.json")
        self.assertTrue(True)
        
    def test_pano_slurp(self):
        #pu.db
        mypano = pano.Pano("testdata2/test_pano_init.json")
        num_files_added = mypano.slurp_images()
        print("num_files_added=%d" % num_files_added)
        self.assertTrue(num_files_added==2642)

    def test_pano_slurp_b1_only(self):
        #pu.db
        mypano = pano.Pano("testdata2/test_pano_b1_only.json")
        num_files_added = mypano.slurp_images()
        print("num_files_added=%d" % num_files_added)
        self.assertTrue(num_files_added==678)
        
    def test_pano_make_pages(self):
        #pu.db
        mypano = pano.Pano("testdata2/test_pano_init.json")
        num_files_added = mypano.slurp_images()
        cam_page_fname_list = mypano.gen_camera_pages(make_derived_files=False)

        self.assertTrue(len(cam_page_fname_list)==2)
        for fname in cam_page_fname_list:
            full_fname = os.path.join("www", fname)
            self.assertTrue(os.path.exists(full_fname))
        #end

        index_fname = mypano.gen_index_page()
        self.assertTrue(os.path.exists(os.path.join("www", index_fname)))
        

    def test_gen_derived_elapsed_mock(self):
        """
        test elapsed time to generate derived files
        """
        #pu.db
        use_mock_test_fcn = True   # dont really generated derived files

        #
        # populate db and get rows corresponding to time interval
        testdata_dir  = 'testdata/FTP-culled'
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, testdata_dir)

        try:
            shutil.rmtree(self.derived_dir)
        except:
            pass
        time_start = time.time()
        derived.make_derived_files(db, num_workers = 1, test_thread_flag=use_mock_test_fcn)
        time_stop = time.time()
        time_one_thread = time_stop - time_start

        #
        # delete all rows to clear the "derived_failed" field
        db.delete_all_rows()
        dirwalk.walk_dir_and_load_db(db, testdata_dir)
        try:
            shutil.rmtree(self.derived_dir)
        except:
            pass
        time_start = time.time()
        derived.make_derived_files(db, num_workers = 2, test_thread_flag=use_mock_test_fcn)
        time_stop = time.time()
        time_two_threads = time_stop - time_start

        time_two_threads = time_stop - time_start
        print("time 1 thread=%f" % time_one_thread)
        print("time 2 thread2=%f" % time_two_threads)
        self.assertTrue(time_two_threads < time_one_thread)


    def test_gen_derived_elapsed(self):
        """
        test elapsed time to generate derived files
        """
        #pu.db
        use_mock_test_fcn = False

        #
        # populate db and get rows corresponding to time interval
        testdata_dir  = 'testdata/FTP-culled'
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, testdata_dir)

        try:
            shutil.rmtree(self.derived_dir)
        except:
            pass
        time_start = time.time()
        derived.make_derived_files(db, num_workers = 1, test_thread_flag=use_mock_test_fcn)
        time_stop = time.time()
        time_one_thread = time_stop - time_start

        #
        # delete all rows to clear the "derived_failed" field
        db.delete_all_rows()
        dirwalk.walk_dir_and_load_db(db, testdata_dir)

        try:
            shutil.rmtree(self.derived_dir)
        except:
            pass
        time_start = time.time()
        derived.make_derived_files(db, num_workers = 2, test_thread_flag=use_mock_test_fcn)
        time_stop = time.time()
        time_two_threads = time_stop - time_start
        print("time 1 thread=%f" % time_one_thread)
        print("time 2 thread2=%f" % time_two_threads)
        self.assertTrue(time_two_threads < time_one_thread)

    def test_derive_twice(self):
        """
        test elapsed time to generate derived files
        """
        try:
            shutil.rmtree(self.derived_dir)
        except:
            pass
        #
        # populate db and get rows corresponding to time interval
        testdata_dir  = 'testdata/FTP-culled'
        db = datastore.Datastore(drop_table_flag=True)
        dirwalk.walk_dir_and_load_db(db, testdata_dir)

        num_deleted = dirwalk.cull_files_by_age(db,
                                             baseline_time='2018-02-26',
                                             derived_dir=self.derived_dir,
                                                max_age_days = 0.33)

        #
        # process media files twice, make sure
        # the 2nd time it doesn't try to reprocess the failures
        time_start = time.time()
        count_success0, count_failed0 = derived.make_derived_files(db,
                                                                   derived_dir=self.derived_dir,
                                                                   num_workers = 2)
        time_stop = time.time()
        time_trial0 = time_stop - time_start

        time_start = time.time()
        count_success1, count_failed1 = derived.make_derived_files(db,
                                                                   derived_dir=self.derived_dir,
                                                                   num_workers = 2)
        time_stop = time.time()
        time_trial1 =  time_stop - time_start

        print("0: success=%d, fail=%d, time=%f" % (count_success0, count_failed0, time_trial0))
        print("1: success=%d, fail=%d, time=%f" % (count_success1, count_failed1, time_trial1))

        self.assertTrue(count_success0==418)
        self.assertTrue(count_failed0==5)
        
        self.assertTrue(count_success1==0)  # no files processed 2nd trial
        self.assertTrue(count_failed1==0)  # no files processed 2nd trial
        

    def test_sleep(self):
        time_start = time.time()
        time.sleep(5.0)  # sleep 5 sec
        time_stop = time.time()
        time_delta = time_stop - time_start
        print("start...stop=%f..%f" % (time_start,time_stop))
        print("diff= %f" % time_delta)
              
        self.assertTrue(time_delta >= 4.8)
        
    def test_two_loops(self):
        mypano = pano.Pano("testdata2/test_pano_init.json")
        num_files_added = mypano.slurp_images()
        cam_page_fname_list = mypano.gen_camera_pages(make_derived_files=False)

        self.assertTrue(len(cam_page_fname_list)==2)
        for fname in cam_page_fname_list:
            full_fname = os.path.join("www", fname)
            self.assertTrue(os.path.exists(full_fname))
        #end
    
        index_fname = mypano.gen_index_page()
        self.assertTrue(os.path.exists(os.path.join("www", index_fname)))
        
    def test_derive_subprocess_mp4(self):
        base_data_dir = 'testdata/FTP-culled'
        path = 'b0/AMC0028V_795UUB/2018-02-25/001/dav/18'
        fname = '18.15.48-18.16.11[M][0@0][0].dav'

        try:
            shutil.rmtree(self.derived_dir)
            os.mkdir(self.derived_dir)
        except:
            pass
        
        derived_fname = derived.convert_dav_to_mp4(base_data_dir, path, fname, self.derived_dir, print_cmd_flag=True)
        print('derived_fname=%s' % derived_fname)
        self.assertTrue(os.path.exists(os.path.join(self.derived_dir, derived_fname)))

    def test_derive_subprocess_jpg(self):
        base_data_dir = 'testdata/FTP-culled'
        path = 'b1/AMC002A3_K2G7HH/2018-02-25/001/jpg/18/09'
        fname = '42[M][0@0][0].jpg'

        try:
            shutil.rmtree(self.derived_dir)
            os.mkdir(self.derived_dir)
        except:
            pass

        derived_fname = derived.make_thumbnail(base_data_dir, path, fname, self.derived_dir, print_cmd_flag=True)
        print('derived_fname=%s' % derived_fname)
        self.assertTrue(os.path.exists(os.path.join(self.derived_dir, derived_fname)))

    def test_subprocess(self):
        cmd = ['ls','-l']
        subprocess.call(cmd)
        self.assertTrue(True)
        
if __name__ == '__main__':
    unittest.main()
    
