from database import *
import os
os.chdir(IMAGE_DIR)
import random
import threading
def ask_loop():
    global number
    while 1:
        number = int(input('Choose number: '), 16)
threading.Thread(target=ask_loop, daemon=True).start()
number = 0
while 1:
    iterated = False
    paths = PathToMigrate.select().where(PathToMigrate.path % ("%/"+hex(number)[2:].zfill(2)+"%")).order_by(fn.Rand()).limit(20).iterator()
    for mod in paths:
        i = mod.path
        i=i.strip()
        if i.endswith('.db') or i.endswith('db-journal'):
            # mod.delete_instance()
            continue
        iterated = True
        try:
            with open(i, 'rb') as o:
                print(i)
                file = o.read()
                File.set_file_content(i.split('/')[-1], file)
                os.unlink(i)
        except FileNotFoundError:
            print(i, 'GONE !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        mod.delete_instance()
    if not iterated:
        print('NO RESULTS!!!! choosing random number')
        number = random.randint(0, 255)
        print('NEW NUM is', number)
