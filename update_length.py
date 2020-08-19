from database import *
import os
for content in Content.select().where(Content.original_length==None).iterator():
    print(repr(content))
    if not content.is_modified():
        content.original_length = content.current_length = os.path.getsize(IMAGE_DIR + content.path)
        content.save()
