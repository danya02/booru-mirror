from database import *
import datetime
import json
import requests
import traceback

def fetch_user(id):
    if id is None:
        return None
    try:
        response = requests.get('https://konachan.net/user.json', params={'id':id}).json()[0]
    except IndexError:
        return
    user = User.get_or_none(User.id==id) or User()
    user.id = id
    user.username = response['name']
    
    
    try:
        user.save(force_insert=True)
    except:
        user.save()
    
    # TODO: work with blacklisted tags
    if response['blacklisted_tags']:
        TempBlacklistedTags.get_or_create(user=user, content=json.dumps(response['blacklisted_tags']))

    return user


if __name__ == '__main__':
    max_id = requests.get('https://konachan.net/user.json').json()[0]['id']
    for i in range(User.select(fn.Max(User.id)).scalar() or 1, max_id):
        print('Fetching user', i)
        fetch_user(i)

