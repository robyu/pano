import sqlite3


class Row:
    d = {}
    
    col_defs = ( \
                 ['cam_name',      'STRING', ''],
                 ['ctime',         'STRING', ''],
                 ['fname',         'STRING', ''],
                 ['has_thumbnail', 'INTEGER', 0],
                 ['mediatype',     'STRING', ''],
                 ['mtime',         'STRING', ''],
                 ['path',          'STRING', ''],
    )
    
    def __init__(self):
        self.d = {}
        for col in Row.col_defs:
            key = col[0]
            default_val = col[2]
            self.d[key] = default_val

class Datastore:
    def __init__(self, db_fname="panodb.sqlite"):
        self.db_fname = db_fname
        self.dbconn = None
        self.tablename = "pano"
        self.cursor = None
        
        self.create_table()
        self.add_cols()

    def create_table(self):
        sqlite_file = './test_db.sqlite'
        self.dbconn = sqlite3.connect(self.db_fname)
        self.cursor = self.dbconn.cursor()
        self.cursor.execute('DROP TABLE IF EXISTS {tn};'.format(tn=self.tablename))
        self.cursor.execute('CREATE TABLE {tn} (id INTEGER PRIMARY KEY)'.format(tn=self.tablename))
        return

    def add_cols(self):
        assert self.cursor!=None
        c = self.cursor
        for entry in Row.col_defs:
            col_name = entry[0]
            col_type = entry[1]
            cmd = "ALTER TABLE {tn} ADD COLUMN {cn} {ct}".format(tn=self.tablename, cn=col_name, ct=col_type)
            c.execute(cmd)
        return

    def add_row(self, row):
        assert self.cursor!=None
        c = self.cursor
        # c.execute("INSERT INTO {tn} (fname, mediatype, path, mtime, ctime, has_thumbnail) " \
        #           " VALUES ({fname}, {mediatype}, {path}, {mtime}, {ctime}, {has_thumbnail})".
        #           format(fname=row.d['fname'], mediatype=row.d['mediatype'], path=row.d['path'],
        #                  mtime=row.d['mtime'], ctime=row.d['ctime'], has_thumbnail=row.d['has_thumbnail']))
        cmd = "INSERT INTO %s " % self.tablename
        col_vector = "("
        val_vector = "("
        num_cols = len(Row.col_defs)
        for n in range(num_cols):
            entry = Row.col_defs[n]
            key = entry[0]
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
        col_vector += ")"
        val_vector += ")"
        cmd = "%s %s VALUES %s" % (cmd, col_vector, val_vector)
        
        c.execute(cmd)

    
    def close(self):
        self.dbconn.close()
        
