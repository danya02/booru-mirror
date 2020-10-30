from database import *

import time
while 1:
    tag = Tag.select().where(~fn.EXISTS(TagPostCount.select(TagPostCount.tag_id).where(TagPostCount.tag_id==Tag.id))).get()
    print('Getting tag', tag.id, 'name', tag.name, 'post count')
    started = time.time()
    count = PostTag.select(fn.COUNT(PostTag.post_id)).where(PostTag.tag == tag).scalar()
    print('Contains', count, 'posts (took', round(time.time()-started, 3), 'seconds)')
    TagPostCount.create(tag=tag, value=count)
    print('~~~~')
