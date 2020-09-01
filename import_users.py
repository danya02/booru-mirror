from database import *
import datetime
import bs4
import requests
import traceback
import random

def fetch_user(id):
    cookies = {
        '__cfduid': 'd2e66dad579d63a99f59ec5986bba30d61597834464',
        'user_id': '750953',
        'pass_hash': 'a5653d305530de9f0f5ad1446c2f378f569e038c',
    }
    params = (
        ('page', 'account'),
        ('s', 'profile'),
        ('id', str(id)),
    )

    response = requests.get('https://rule34.xxx/index.php', params=params, cookies=cookies)
    resp_parsed = bs4.BeautifulSoup(response.text, "html.parser").find(id='content')
    user = User(id=id)
    user.username = resp_parsed.h2.text.strip()
#    return resp_parsed
#    return (resp_parsed.table.contents[1])
    join_date_row = resp_parsed.table.contents[3]
    join_date = join_date_row.contents[3].text
    if 'N/A' in join_date:
        return
    if not user.username:
        raise ValueError('Username empty, better not continue')
    acc_level = resp_parsed.table.contents[5].contents[3].text.strip()
    user.join_date = datetime.date(*[int(i) for i in join_date.split('-')])
    level, _ = AccessLevel.get_or_create(name=acc_level)
    user.level = level
    try:
        user.save(True)
    except:
        user.save()

if __name__ == '__main__':
#    for i in range(32310, 750954):
#        try:
#            db.execute_sql('INSERT INTO `user` (`id`) VALUES (%s)', i)
#        except:
#            pass
    while 1:
        for i in User.select(User.id).where(User.username == None).order_by(fn.Rand()).limit(25).iterator():
            print('Fetching user', i.id)
            fetch_user(i.id)

