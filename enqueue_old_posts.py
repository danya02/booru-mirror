from database import *
while 1:
    for i in DownloadedPost.select(DownloadedPost.id).order_by(fn.Rand()).limit(10).iterator():
        QueuedPost.get_or_create(id=i.id)
        print(i.id)
