import sqlite3

class Datastore:
    def __init__(self, db_fname="panodb.sqlite"):
        self.db_fname = db_fname
        self.tablename = "pano"
        self.connection = None
        self.cursor = None
        
        self.create_table()
        self.add_cols()

    def create_table(self):
        sqlite_file = './test_db.sqlite'
        self.dbconn = sqlite3.connect(self.db_fname)
        self.cursor = self.dbconn.cursor()
        self.cursor.execute('DROP TABLE IF EXISTS {tn};'.format(tn=self.tablename))
        self.cursor.execute('CREATE TABLE {tn} (id INTEGER)'.format(tn=self.tablename))
        return

    def add_cols(self):
        assert self.cursor!=None
        c = self.cursor
        c.execute("ALTER TABLE {tn} ADD COLUMN fname STRING".format(tn=self.tablename))
        c.execute("ALTER TABLE {tn} ADD COLUMN mediatype STRING".format(tn=self.tablename))
        c.execute("ALTER TABLE {tn} ADD COLUMN path STRING".format(tn=self.tablename))
        c.execute("ALTER TABLE {tn} ADD COLUMN mtime STRING".format(tn=self.tablename))
        c.execute("ALTER TABLE {tn} ADD COLUMN ctime STRING".format(tn=self.tablename))
        c.execute("ALTER TABLE {tn} ADD COLUMN has_thumbnail INTEGER".format(tn=self.tablename))
        return
    
    def close(self):
        self.dbconn.close()
        
        
        
        
