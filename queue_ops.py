from database import *
import datetime
import itertools
import random


def enqueue_many(values, type):
    for chunk in chunked(values, 10000):
        print(chunk[0], '==>', chunk[-1])
        types = itertools.repeat(type)
        times = itertools.repeat(datetime.datetime.now())
        QueuedDownload.insert_many(zip(chunk, types, times), fields=[QueuedDownload.entity_id, QueuedDownload.entity_type, QueuedDownload.enqueued_when]).execute()

def fetch_single(type):
#    target_id = random.randint(*QueuedDownload.select(fn.Min(QueuedDownload.entity_id), fn.Max(QueuedDownload.entity_id)).where(QueuedDownload.entity_type == type).scalar(as_tuple=True))
#    target_clause = (QueuedDownload.entity_id >= target_id)
    if random.randint(1, 50)==1:
        answer = QueuedDownload.select().where(QueuedDownload.entity_type==type).get()
        print('Selecting item from beginning:', answer.entity_type, answer.entity_id)
        return answer
    count = QueuedDownload.select(fn.Count(QueuedDownload.id)).where(QueuedDownload.entity_type == type).scalar()
    print('Queue contains', count, type)
    answer = QueuedDownload.select().where(QueuedDownload.entity_type == type).limit(1).offset(random.randint(0, count))
    answer = list(answer)[0]
    print('Fetched', type, answer.entity_id, '(', answer.id, ')')
    return answer

def fetch_many(type):
    while True:
        yield fetch_single(type)


def accept_single(row):
    print('Accepted', row.entity_type, row.entity_id, '(', row.id, ')')
    with db.atomic():
        row.delete_instance()
        CompletedDownload.create(entity_id=row.entity_id, entity_type=row.entity_type, completed_when=datetime.datetime.now())

def accept_by_id(entity_id, entity_type):
    print('Accepted by id', entity_type, entity_id)
    with db.atomic():
        queued = QueuedDownload.get_or_none(QueuedDownload.entity_id == entity_id, QueuedDownload.entity_type == entity_type)
        if queued is not None:
            queued.delete_instance()
        CompletedDownload.create(entity_id=entity_id, entity_type=entity_type, completed_when=datetime.datetime.now())

if __name__ == '__main__':
    start = int(input('Min value inclusive:'))
    end = int(input('Max value exclusive: '))
    type = input('type: ')
    enqueue_many(range(start, end), type)
