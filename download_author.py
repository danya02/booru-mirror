from database import *
import datetime
import requests
from import_users import fetch_user

def get_author(name, id, force_download_pic=False):
    u = User.get_or_none(User.id == id) or User.get_or_none(User.username == name)
#    if id is None:
#        return None
    if u is not None and u.username is not None:
        if u.profile_picture is None or force_download_pic:
            download_author_profpic(u)
        return u
    u = fetch_user(id)
    u.id = id
    if u is None:
        return None
    if u.profile_picture is None or force_download_pic:
        download_author_profpic(u)
    return u

get_user = get_author

def download_author_profpic(u):
    req = requests.get(f'https://' + SITE + '/data/avatars/{u.id}.jpg')
    try:
        req.raise_for_status()
    except:
        return
    u.profile_picture = req.content
    u.profile_picture_mimetype = req.headers.get('content-type')
    u.profile_picture_fetched_at = datetime.datetime.now()
    u.save()



if __name__ == '__main__':
    max_id = requests.get('https://' + SITE + '/user.json').json()[0]['id']
    for i in range(User.select(fn.Max(User.id)).where(User.profile_picture.is_null(False)).scalar() or 1, max_id):
        print('Fetching user', i)
        get_author(None, i)
