from database import *
import os
os.chdir(IMAGE_DIR)
while 1:
    paths = PathToMigrate.select().order_by(fn.Rand()).limit(200).iterator()
    for mod in paths:
        i = mod.path
        i=i.strip()
#        if i.endswith('.db') or i.endswith('db-journal'):
#            mod.delete_instance()
#            continue
        folder = '/'.join(i.split('/')[:-1])
        try:
            os.makedirs(f'/data/MIGRATION/rule34.xxx/{folder}')#f'/mnt/migration-3/MIGRATION/rule34.xxx/{folder}')
        except FileExistsError:
            pass
        os.system(f'mv -v "{i}" "/data/MIGRATION/rule34.xxx/{i}"')#f'mv -v "{i}" "/mnt/migration-3/MIGRATION/rule34.xxx/{i}"')
        mod.delete_instance()
