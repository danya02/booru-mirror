from database import *
from download import get_author
import requests
import datetime


def download_post_comments(post):
    comments = requests.get('https://konachan.net/comment.json', params={'post_id': post.id}).json()
    for i in comments:
        get_comment(i['id'], content=i, visited={post.id: post})

def get_comment(id, content=None, visited=None):
    visited = visited or dict()
    content = content or requests.get('https://konachan.net/comment/show.json', params={'id': id})
    c = Comment.get_or_none(Comment.id == id)
    if c is None:
        c = Comment()
        c.id = id
    c.created_at = datetime.datetime.fromisoformat(content['created_at'][:-1])
    c.score = content['score']
    c.post = None # visited.get(content['post_id'])
    if c.post is None:
        print('!!! Getting post', content['post_id'], 'without comments! This should not happen normally!')
        c.post = get_post(content['post_id'], visited=visited)
    c.author = get_author(content['creator'], content['creator_id'])
    c.body = content['body']
    try:
        c.save()
    except:
        c.save(force_insert=True)
    return c

