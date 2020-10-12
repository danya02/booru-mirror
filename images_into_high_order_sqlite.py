from database import *
import sqlite3
import os
os.chdir(IMAGE_DIR)
while 1:
    paths = PathToMigrate.select().where(PathToMigrate.path % ("./%%/%%%%.db")).iterator()
    for mod in paths:
        i = mod.path
        i=i.strip()
        if len(i.split('/')[-1].split('.')[0])==2: 
            print('NOT CONTINUING WITH', i)
            continue
        conn = sqlite3.connect(i)
        cursor = conn.cursor()
        print('OPENED', i)
        looped = False
        try:
            for name, data in cursor.execute('select * from file;'):
                looped = True
                File.set_file_content(name, data)
                del_cur = conn.cursor()
                print('DELETED', name, 'FROM', i)
                del_cur.execute('delete from file where name=?;', (name,))
                conn.commit()
        except: pass
        try:
            conn.execute('vacuum')
        except: pass
        conn.close()
        if not looped:
            print('DB EMPTY, DELETING', i)
            os.unlink(i)
            mod.delete_instance()
