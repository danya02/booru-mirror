from database import *
import os
os.chdir(IMAGE_DIR)
paths = os.popen('find -type f')

for i in paths:
    i=i.strip()
    if i.endswith('.db') or i.endswith('db-journal'):
        continue
    with open(i, 'rb') as o:
        print(i)
        file = o.read()
        File.set_file_content(i.split('/')[-1], file)
        os.unlink(i)
