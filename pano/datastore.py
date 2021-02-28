import sqlite3
import logging
import datetime
import timeit

"""
"""    

MEDIA_UNKNOWN = 0
MEDIA_IMAGE = 1
MEDIA_VIDEO = 2

class Row:
    d = {}
    
    col_defs = ( \
                 ['id',            'INTEGER PRIMARY KEY', ''],
                 ['base_data_dir', 'STRING',   ''],
                 ['cam_name',      'STRING',   ''],
                 ['ctime',         'STRING',   ''],
                 ['ctime_unix',    'INTEGER',  -1],
                 ['fname',         'STRING',   ''],
                 ['derive_failed', 'INTEGER',   0],
                 ['derived_fname', 'STRING',   ''],
                 ['mediatype',     'INTEGER',   0],
                 ['path',          'STRING',   '']
    )
    
    def __init__(self):
        self.d = {}
        for col in Row.col_defs:
            key = col[0]
            default_val = col[2]
            self.d[key] = default_val

    def db_entry_to_row(self, entry):
        """
        (1, u'b0', u'2018-02-24T00:03:07', 1519401787, u'00.03.07-00.03.31[M][0@0][0].dav', 0, u'dav', u'',                                                         
        u'testdata/FTP/b0/AMC0028V_795UUB/2018-02-24/001/dav/00')
        """
        self.d['id']            = entry[0]
        self.d['base_data_dir'] = entry[1]
        self.d['cam_name']      = entry[2]
        self.d['ctime']         = entry[3]
        self.d['ctime_unix']    = entry[4]
        self.d['fname']         = entry[5]
        self.d['derive_failed'] = entry[6]
        self.d['derived_fname'] = entry[7]
        self.d['mediatype']     = entry[8]
        self.d['path']          = entry[9]
            
class Datastore:
    
    def __init__(self, db_fname="panodb.sqlite", drop_table_flag=False):
        self.db_fname = db_fname
        self.dbconn = None
        self.tablename = "pano"
        self.cursor = None
        
        self.create_table(drop_table_flag)

        #
        # there doesn't seem to be any way to determine if the sqlite database
        # already has the tables set up, so try to add the columns
        # and catch any errors with exceptions:
        # try:
        #     self.add_cols()
        # except sqlite3.OperationalError:
        #     pass
            

    def create_table(self, drop_table_flag=False):
        self.dbconn = sqlite3.connect(self.db_fname)
        self.cursor = self.dbconn.cursor()
        if drop_table_flag==True:
            self.cursor.execute('DROP TABLE IF EXISTS {tn};'.format(tn=self.tablename))
        #end
        cmd =  'CREATE TABLE IF NOT EXISTS {tn} ('.format(tn=self.tablename)

        #
        # each column definition
        for entry in Row.col_defs:
            col_name = entry[0]
            col_type = entry[1]
            cmd = cmd + "{cn} {ct}".format(cn=col_name, ct=col_type)
            cmd = cmd + ", "
        #end
        cmd = cmd + "unique (path, fname) ON CONFLICT IGNORE)"
        retval = self.cursor.execute(cmd)

        return

    def add_cols(self):
        assert self.cursor!=None
        c = self.cursor
        for entry in Row.col_defs:
            col_name = entry[0]
            col_type = entry[1]
            if col_name=="id":
                continue
            #end

            cmd = "ALTER TABLE {tn} ADD COLUMN {cn} {ct}".format(tn=self.tablename, cn=col_name, ct=col_type)
            c.execute(cmd)
        return

    def add_row(self, row):
        """
        add row to database
        if it's a duplicate row, then don't re-add it
        (this is handled by the table UNIQUE constraint)

        returns:
        none
        """

        assert self.cursor!=None
        c = self.cursor
        # c.execute("INSERT INTO {tn} (fname, mediatype, path, mtime, ctime, has_derived) " \
        #           " VALUES ({fname}, {mediatype}, {path}, {mtime}, {ctime}, {has_derived})".
        #           format(fname=row.d['fname'], mediatype=row.d['mediatype'], path=row.d['path'],
        #                  mtime=row.d['mtime'], ctime=row.d['ctime'], has_derived=row.d['has_derived']))

        # if ctime_unix is < 0, then compute ctime_unix
        if row.d['ctime_unix'] < 0:
            unix_time = self.iso8601_to_sec(row.d['ctime'])
            row.d['ctime_unix'] = unix_time
        #end

        cmd = "INSERT INTO %s " % self.tablename
        col_vector = "("
        val_vector = "("
        num_cols = len(Row.col_defs)
        for n in range(num_cols):
            entry = Row.col_defs[n]
            key = entry[0]
            if key == "id":
                continue

            col_vector += " %s" % key
            if entry[1]=='INTEGER':
                val_vector += " %d" % row.d[key]
            elif entry[1]=='STRING':
                val_vector += """ \'%s\'""" % row.d[key]
            else:
                assert False, "unhandled column type"

            if n < num_cols-1:
                col_vector += ","
                val_vector += ","
            #end
        #end
        col_vector += ")"
        val_vector += ")"
        cmd = "%s %s VALUES %s" % (cmd, col_vector, val_vector)
        logging.debug("adding row (%s)" % cmd)
        c.execute(cmd)
        logging.debug("success!")

    def entries_to_rows(self, entry_list):
        """
        convert list of database entries
        to list of row objects

        returns
        row_list
        """
        row_list=[]
        for n in range(len(entry_list)):
            row = Row()
            row.db_entry_to_row(entry_list[n])
            row_list.append(row)
        #end
        return row_list
        
    def select_all(self):
        cmd = "select * from {tn}".format(tn=self.tablename)
        self.cursor.execute(cmd)
        entry_list = self.cursor.fetchall()

        row_list = self.entries_to_rows(entry_list)
        return row_list

        
    def iso8601_to_sec(self, strtime):
        """
        convert a string time, such as '2018-03-27T03:03:00' or 'now' (in localtime)
        into UTC epoch time in seconds

        see https://www.techonthenet.com/sqlite/functions/datetime.php
        """
        if strtime=="now":
            #
            # requests for "now" are treated differently: do not specify "utc", otherwise we get
            # the wrong timezone
            cmd = "select strftime('%s','{strtime}')".format(strtime=strtime)
        else:
            cmd = "select strftime('%s','{strtime}','utc')".format(strtime=strtime)
        #end
        self.cursor.execute(cmd)
        ret = self.cursor.fetchall()
        sec = int(ret[0][0])
        # if strtime=="now":
        #     logging.info("strtime=='now'")
        #     logging.info("system time currently: %s" % datetime.datetime.now())
        #     logging.info("epoch time (%d) -> iso8601 (%s)" % (sec, self.sec_to_iso8601(sec)))
        return sec

    def sec_to_iso8601(self, sec):
        """
        convert UTC epoch time (seconds) to iso8601 timestring
        see https://www.techonthenet.com/sqlite/functions/datetime.php
        """
        cmd = "select datetime(%d, 'unixepoch','localtime')" % sec
        self.cursor.execute(cmd)
        ret = self.cursor.fetchall()
        return ret[0][0]
        

    def select_older_than(self, baseline_time=None, max_age_days=14):
        """
        given baseline_time
        max_age_days

        return list of row entries which are older than baseline_time - threshold_days

        for testing:
        '2018-02-26' -> 1519632000
        28800 sec = 8 hours
        2018-02-26-8 hours..2018-02-26 yields 445 rows

        """
        # select * from pano where ctime_unix between 1519614800 and 1519614862
        
        #
        # compute epoch time for threshold epoch = baseline_time - cull days
        # if baseline_time==None:
        #     baseline_time="'now'"
        assert (max_age_days > 0) and (max_age_days < 60)
        
        baseline_unix = self.iso8601_to_sec(baseline_time)
        age_sec = int(max_age_days * 24.0 * 60 * 60)
        assert baseline_unix-age_sec > 0
        #cmd = "select * from {tn} where ctime_unix < {thresh}".format(tn=self.tablename,
        #    thresh=thresh_unix)
        
        cmd = "select * from {tn} where ctime_unix < {start}".format(tn=self.tablename,
                                                                     start = baseline_unix - age_sec)
        self.cursor.execute(cmd)
        entry_list= self.cursor.fetchall()

        row_list = self.entries_to_rows(entry_list)

        return row_list

    def select_latest_image_per_camera(self,cam_name):
        """
        get latest entry, 1 per camera, with a derived image
        
        returns list of row entries
        """
        cmd = "select *, max(ctime_unix) from {tn} where cam_name='{cam_name}'" \
        " AND mediatype={mediatype}" \
        " AND length(derived_fname) > 0" \
        " AND derive_failed==0".format(tn=self.tablename,
                                       cam_name=cam_name,
                                       mediatype=MEDIA_IMAGE)
        self.cursor.execute(cmd)
        entry_list = self.cursor.fetchall()
        # NOTE: if no entry is found which meets the query,
        # entry_list will contain a single tuple which is all "None"
        # this condition is awkward to detect, so handle it downstream.

        row_list = self.entries_to_rows(entry_list)

        assert len(row_list)==1
        return row_list
    
    @timeit.timeit
    def select_by_age_range(self, baseline_time=None, max_age_days=14):
        """
        given baseline_time
        max_age_days

        return list of row entries which fall into range baseline_time - threshold_days..baseline

        for testing:
        '2018-02-26' -> 1519632000
        28800 sec = 8 hours
        2018-02-26-8 hours..2018-02-26 yields 445 rows

        """
        # select * from pano where ctime_unix between 1519614800 and 1519614862
        
        #
        # compute epoch time for threshold epoch = baseline_time - cull days
        # if baseline_time==None:
        #     baseline_time="'now'"
        assert (max_age_days > 0) and (max_age_days < 60)
        
        baseline_unix = self.iso8601_to_sec(baseline_time)
        age_sec = int(max_age_days * 24.0 * 60 * 60)
        assert baseline_unix-age_sec > 0
        #cmd = "select * from {tn} where ctime_unix < {thresh}".format(tn=self.tablename,
        #    thresh=thresh_unix)
        
        cmd = "select * from {tn} where ctime_unix between {start} and {stop}".format(tn=self.tablename,
                                                                                      start = baseline_unix - age_sec,
                                                                                      stop = baseline_unix)
        self.cursor.execute(cmd)
        entry_list= self.cursor.fetchall()

        row_list = self.entries_to_rows(entry_list)

        return row_list

    def update_row(self, id, col, val):
        """
        update database entry's column:value 
        """
        if isinstance(val, str):
            cmd = "update {tn} set {col}='{val}' where id={id}".format(tn=self.tablename, col=col,val=val,id=id)
        else:
            cmd = "update {tn} set {col}={val} where id={id}".format(tn=self.tablename, col=col,val=val,id=id)
        #end
        logging.debug("execute sql: (%s)" % cmd)
        self.cursor.execute(cmd)
        self.dbconn.commit()

        #print("updated row %d" % id)
        return

    def select_by_id(self, id):
        """
        select db entry based on id

        returns:
        selected row
        """

        cmd = "select * from {tn} where id={id}".format(tn=self.tablename, id=id)
        self.cursor.execute(cmd)
        entry = self.cursor.fetchall()
        assert len(entry)==1
        row = Row()
        row.db_entry_to_row(entry[0])
        return row

    def delete_row(self, row):
        """
        delete row from database
        """
        cmd = "delete from {tn} where id={id}".format(tn=self.tablename, id=row.d['id'])
        self.cursor.execute(cmd)
        return

    def delete_all_rows(self):
        """
        delete all rows (for testing)
        """
        cmd = "delete from {tn}".format(tn=self.tablename)
        self.cursor.execute(cmd)
        return
    
    def select_by_time_cam_media(self, cam_name, upper_time_sec, lower_time_sec, mediatype):
        """
        select db entries based on criteria
        
        return:
        list of selected rows
        """
        cmd = "select * from {tn} where (cam_name='{cam_name}')"\
              " AND (ctime_unix > {lower_time})"\
              " AND (ctime_unix <= {upper_time})"\
              " AND (mediatype={mediatype})"\
              .format(tn=self.tablename,
                      cam_name=cam_name,
                      upper_time = upper_time_sec,
                      lower_time = lower_time_sec,
                      mediatype=mediatype)
        self.cursor.execute(cmd)
        entry_list = self.cursor.fetchall()
        row_list = self.entries_to_rows(entry_list)
        return row_list

    def select_by_cam(self, cam_name):
        """
        select db entries based on criteria
        
        return:
        list of selected rows
        """
        cmd = "select * from {tn} where (cam_name='{cam_name}')"\
              .format(tn=self.tablename,
                      cam_name=cam_name)
        self.cursor.execute(cmd)
        entry_list = self.cursor.fetchall()
        row_list = self.entries_to_rows(entry_list)
        return row_list

    def close(self):
        self.dbconn.close()
        
