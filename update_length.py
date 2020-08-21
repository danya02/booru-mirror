from database import *
import os
import threading
def custom_rows():
    while 1:
        id = int(input())
        content = Content.get_by_id(id)
        print(repr(content))
        if not content.is_modified():
            content.original_length = content.current_length = os.path.getsize(IMAGE_DIR + content.path)
            content.save()
threading.Thread(target=custom_rows).start() 

for content in Content.select().where(Content.original_length==None).iterator():
    print(repr(content))
    if not content.is_modified():
        content.original_length = content.current_length = os.path.getsize(IMAGE_DIR + content.path)
        content.save()
