from database import *
import requests
import traceback
from download_author import get_author
import queue_ops


def get_forumpost(id, update_if_exists=False, visited=None):
    visited = visited or dict()
    if id in visited:
        return visited[id]
    fp = ForumPost.get_or_none(ForumPost.id == id)
    if fp and update_if_exists:
        return fp
    req = requests.get(f'https://' + SITE + '/forum/show/{id}.json').json()
    if req.get('status') == '404':
        return None
    insert = fp is None
    fp = fp or ForumPost()
    fp.id = id
    fp.title = req['title'] or None
    fp.body = req['body']
    fp.creator = get_author(req['creator'], req['creator_id'])
    fp.updated_at = datetime.datetime.fromisoformat(req['updated_at'][:-1])
    fp.pages = req['pages']
    visited.update({id: fp})
    fp.parent = get_forumpost(req['parent_id'], visited=visited)
    
    
    fp.save(force_insert=insert)
    return fp

if __name__ == '__main__':
    latest = requests.get('https://' + SITE + '/forum.json?latest=1').json()
    target_id = max(latest, key=lambda x: x['id'])['id']
    start_id = ForumPost.select(fn.Max(ForumPost.id)).scalar()
    print('Enqueueing', start_id, '-->', target_id)
    queue_ops.enqueue_many(range(start_id, target_id), 'forum')

    while True:
        q = queue_ops.fetch_single('forum')
        get_forumpost(q.entity_id)
        queue_ops.accept_single(q)
