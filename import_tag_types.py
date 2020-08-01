from database import *
import requests
import bs4
import queue
import threading

def get_page(num):
    r = requests.get('https://rule34.xxx/index.php?page=tags&s=list&pid='+str(num*50)).text
    p = bs4.BeautifulSoup(r, 'html.parser')
    tags = p.find_all('tr')
    name_type = []
    for i in tags:
        if i.get('class') is not None:
            continue
        if len(i.find_all('td'))!=3:
            continue
        num, name, types = i.find_all('td')
        name = name.get_text()
        types = types.get_text().split('(')[0].split(',')
        types = [i.strip() for i in types]
        name_type.append((name, types))

    return name_type

INTO_DB = queue.Queue(1000)

def put_into_db():
    while 1:
        try:
            tag, types = INTO_DB.get(timeout=5)
        except:
            print('==== TIMEOUT ====')
            continue
        try:
            tag_row = Tag.get(Tag.name==tag)
        except:
            print('No tag by name', tag)
            INTO_DB.task_done()
            continue

        for type_name in types:
            type_row, type_created = Type.get_or_create(name=type_name)
            tt, created = TagType.get_or_create(tag=tag_row, type=type_row)
            if created:
                print('Created link', tag, '-->', type_name)
            else:
                print('Link already exists:', tag, '-->', type_name)
        INTO_DB.task_done()

for i in range(4):
    threading.Thread(target=put_into_db).start()

for page in range(9000):
    print('Loading page', page)
    for element in get_page(page):
        INTO_DB.put(element)
