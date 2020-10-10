from database import *
import os
os.chdir(IMAGE_DIR)
find = os.popen('find -type f')
for line in find:
    line = line.strip()
    print(PathToMigrate.get_or_create(path=line))
