from database import *
from download_author import get_author
import requests
import datetime
import traceback
import queue_ops


def download_post_notes(post):
    notes = requests.get('https://' + SITE + '/note.json', params={'post_id': post.id}).json()
    for i in notes:
        get_note(i['id'], content=i, visited={post.id: post})

def get_note(id, content=None, visited=None):
    visited = visited or dict()
    if content is None:
        content_list = requests.get('https://' + SITE + '/note/history.json', params={'id': id}).json()
    else:
        content_list = [content]
    for content in content_list:
        n = Note.get_or_none(Note.id == id, Note.version == content['version'])
        if n is None:
            n = Note()
            n.id = id
            n.version = content['version']
        n.created_at = datetime.datetime.fromisoformat(content['created_at'][:-1])
        n.updated_at = datetime.datetime.fromisoformat(content['updated_at'][:-1])
        n.x = content['x']
        n.y = content['y']
        n.width = content['width']
        n.height = content['height']


        n.post = visited.get(content['post_id']) or None
        if n.post_id is None:
            print('!!! Getting post', content['post_id'], 'without notes! This should not happen normally!')
            n.post = get_post(content['post_id'], visited=visited)
        n.author = get_author(content.get('creator'), content['creator_id'])
        n.body = content['body']
        n.is_active = content['is_active']
        try:
            n.save(force_insert=True)
        except IntegrityError:
            traceback.print_exc()
            n.save()
    queue_ops.accept_by_id(id, 'note')

