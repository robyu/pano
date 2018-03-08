#!/usr/bin/env python

import sqlite3
import dirwalk
import unittest
import time
import subprocess
import os
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
        col_id = 'id'
        col_id_type = 'INTEGER'
        
        col_fname = 'filename'
        col_fname_type = 'STRING'

        col_mtime = 'mtime'
        col_mtime_type = 'STRING'
        
        sqlite_file = './test_db.sqlite'
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS {tn};' \
                  .format(tn=table_name))
        c.execute('CREATE TABLE {tn} ({col_id} {col_id_type})' \
                  .format(tn=table_name, col_id=col_id, col_id_type=col_id_type))

        c.execute("ALTER TABLE {tn} ADD COLUMN '{col_fname}' {col_fname_type}" \
                  .format(tn=table_name, col_fname=col_fname, col_fname_type=col_fname_type))

        conn.close()
        self.assertTrue(True)



        
if __name__ == '__main__':
    unittest.main()
    




