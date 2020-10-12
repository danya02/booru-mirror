from database import *

#start = QueuedPost.select(fn.Max(QueuedPost.id)).scalar()+2
start = 1
end = int(input('Current max post: '))

for chunk in chunked(range(start, end), 10000):
    print(chunk[0], '==>', chunk[-1])
    QueuedPost.insert_many(zip(chunk), fields=[QueuedPost.id]).execute()
