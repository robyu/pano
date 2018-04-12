#!/usr/bin/env python

import sqlite3
import dirwalk
import unittest
import time
import subprocess
import os
import datastore
import pudb

"""
run all unit tests
python -m unittest runtests.py

run an individual test
python -m unittest testica.TestIca.test_smoketest   # works with pu.db in code
"""

class TestPano(unittest.TestCase):
    test_data_dir = './testdata/FTP'

    def setUp(self):
        print("setup")
        subprocess.call(['./restore-testdata.sh'])

    def test_cull_files_by_ext(self):
        pu.db
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

    def test_select_by_age(self):
        pu.db
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
        pu.db
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
        pu.db
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
        pu.db
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP')
        num_deleted = dirwalk.cull_files_by_age(db,
                                                root_dir='testdata/FTP',
                                                baseline_time='2018-02-26',
                                                max_age_days=0.25)
        dirwalk.make_derived_files(db, root_dir='testdata/FTP')
        db.close()
        
if __name__ == '__main__':
    unittest.main()
    


