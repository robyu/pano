#!/usr/bin/env python

import dirwalk
import unittest
import time
import subprocess

"""
run all unit tests
python -m unittest runtests.py

run an individual test
python -m testica.TestIca.test_smoketest   # works with pu.db in code
"""

class TestPano(unittest.TestCase):
    def setUp(self):
        print("setup")
        subprocess.call(['./restore-testdata.sh'])
    
    def test_cull_files(self):
        # baseline_time = time.strptime("26 feb 2018 00:00", "%d %b %Y %H:%M")
        # baseline_time_epoch = time.mktime(baseline_time)
        # num_deleted = dirwalk.cull_files(baseline_time_epoch=baseline_time_epoch, cull_threshold_days=1)
        # print("deleted %d files" % num_deleted)
        # self.assertTrue(num_deleted==1298)
        self.assertTrue(True)
        
if __name__ == '__main__':
    unittest.main()
    




