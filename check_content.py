from database import *

for i in Content.select().iterator():
    flen = File.get_length(i.path)
    print(i.path, flen)
    if flen is None:
        i.delete_instance()
    else:
        i.current_length = i.original_length = flen
