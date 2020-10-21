from database import *
from download_author import get_author
import requests
from download_post import get_post
import datetime
import queue_ops
import traceback


def download_post_comments(post):
    comments = requests.get('https://' + SITE + '/comment.json', params={'post_id': post.id}).json()
    for i in comments:
        get_comment(i['id'], content=i, visited={post.id: post})

def get_comment(id, content=None, visited=None):
    visited = visited or dict()
    content = content or requests.get('https://' + SITE + '/comment/show.json', params={'id': id})
    c = Comment.get_or_none(Comment.id == id)
    if c is None:
        c = Comment()
        c.id = id
    c.created_at = datetime.datetime.fromisoformat(content['created_at'][:-1])
    c.score = content.get('score')
    c.post = visited.get(content['post_id']) or None
    if c.post_id is None:
        print('!!! Getting post', content['post_id'], 'without comments! This should not happen normally!')
        c.post = get_post(content['post_id'], visited=visited)
    c.author = get_author(content.get('creator'), content['creator_id'])
    c.body = content['body']
    try:
        c.save(force_insert=True)
    except IntegrityError:
        c.save()
    queue_ops.accept_by_id(id, 'comment')
    return c

