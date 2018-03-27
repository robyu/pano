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
        num_deleted = dirwalk.cull_files_by_ext(root_dir=self.test_data_dir)
        print("num_deleted = %d" % num_deleted)
        self.assertTrue(num_deleted==290)
        
    def test_cull_files_by_age(self):
        baseline_time = time.strptime("26 feb 2018 00:00", "%d %b %Y %H:%M")
        baseline_time_epoch = time.mktime(baseline_time)
        num_deleted = dirwalk.cull_files_by_age(baseline_time_epoch=baseline_time_epoch, cull_threshold_days=1.75,root_dir=self.test_data_dir)
        print("deleted %d files" % num_deleted)
        self.assertTrue(num_deleted==136)
        self.assertTrue(True)

    def test_cull_empty_dirs(self):
        dirwalk.cull_empty_dir(self.test_data_dir)

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
        db.cursor.execute("INSERT INTO {tn} (fname, path, has_thumbnail) VALUES ('abcd', 'xyz', 1)".format(tn=db.tablename))
        db.cursor.execute("INSERT INTO {tn} (fname, path, has_thumbnail) VALUES ('efgh', '123', 0)".format(tn=db.tablename))
        #db.dbconn.commit()
        db.cursor.execute('SELECT * FROM {tn} WHERE fname like "%a%"'.format(tn=db.tablename))
        all_rows = db.cursor.fetchall()
        print(all_rows)
        print(len(all_rows))
        db.close()
        self.assertTrue(len(all_rows)==1)

    def test_walk_dir_and_store(self):
        pu.db
        db = datastore.Datastore()
        dirwalk.walk_dir_and_load_db(db, 'testdata/FTP')
        db.close()

        
if __name__ == '__main__':
    unittest.main()
    


