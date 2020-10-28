from database import *
import requests
import traceback
from download_author import get_author
import queue_ops

session = requests.session()
session.proxies = {}
session.proxies['http'] = 'socks5h://localhost:9050'
session.proxies['https'] = 'socks5h://localhost:9050'

def get_forumpost(id, update_if_exists=False, visited=None):
    visited = visited or dict()
    if id in visited:
        return visited[id]
    fp = ForumPost.get_or_none(ForumPost.id == id)
    if fp and update_if_exists:
        return fp
    req = session.get(f'https://' + SITE + '/forum/show/{id}.json')
    print(req.text)
    req = req.json()
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
    while True:
        q = queue_ops.fetch_single('forum')
        get_forumpost(q.entity_id)
        queue_ops.accept_single(q)
