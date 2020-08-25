import bs4
import requests
from database import *
import datetime
import queue
import traceback
import os
import random
CACHE = dict()

LAST = 0
INTO_DB = queue.Queue(1000)

def put_into_db(timeout=600):
    while 1:
        try:
            model, force, on_done = INTO_DB.get(timeout=timeout)
        except KeyboardInterrupt: return
        except:
            print('==== TIMEOUT ====')
            return
        try:
            if model is not None:
                model.save(force_insert=force)
            print('        Inserted', repr(model))
            print('        Current qsize:', INTO_DB.qsize())
        except:
            print('UNIQUE CONSTRAINT FAILED !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            traceback.print_exc()
        on_done()
        INTO_DB.task_done()

def save(model, force_insert=False, on_done=lambda: None):
    INTO_DB.put((model, force_insert, on_done))

def real_fetch(url, and_cache=True):
#    print('Downloading', url)
    with requests.get(url) as req:
        b = bs4.BeautifulSoup(req.text, features="html.parser")
        if and_cache:
            CACHE[url] = b
    return b

def prefetch():
    ind = 0
    while 1:
        ind += 1
        ind = max(ind, LAST+5)
        real_fetch(f'https://{SITE}/index.php?page=dapi&s=post&q=index&id={ind}')
        real_fetch(f'https://{SITE}/index.php?page=post&s=view&id={ind}&pid=0')
        real_fetch(f'https://{SITE}/index.php?page=dapi&s=comment&q=index&post_id={ind}')
        real_fetch(f'https://{SITE}/index.php?page=dapi&s=note&q=index&post_id={ind}')

def fetch(url):
#    try:
#        return CACHE.pop(url)
#    except KeyError:
    return real_fetch(url, and_cache=False)

def get_page(num):
    return fetch(f'https://{SITE}/index.php?page=dapi&s=post&q=index&limit=100&pid={num}').findAll('post')

def get_post(id):
    try:
        return fetch(f'https://{SITE}/index.php?page=dapi&s=post&q=index&id={id}').findAll('post')[0]
    except IndexError:
        return None

def get_author(id, name=None):
    try:
        author = User.get(User.id == (id or 2))  # 2 is the ID for anonymous
        author.username = author.username or name
        save(author)
    except User.DoesNotExist:
        author = User()
        author.id = id
        author.name = name
        save(author, True)
    return author
        

def create_post(post, and_comments=True, and_notes=True, and_download=True, past_posts=dict()):
    if not post:
        print('This post is None')
        return None
    try:
        p = Post.get(Post.id==int(post['id']))
        create = False
    except Post.DoesNotExist:
        p = Post()
        create = True
    if (create or int(post['change']) > p.changed_at.timestamp()) or True:
        p.id = int(post['id'])
        print('Loading post', p.id)
        p.created_at = datetime.datetime.strptime(post['created_at'], '%a %b %d %H:%M:%S %z %Y')
        p.changed_at = datetime.datetime.fromtimestamp(int(post['change']))

        p.creator = get_author(post['creator_id'])

        p.height = int(post['height'])
        p.width = int(post['width'])
        p.url = post['file_url']
        p.md5 = post['md5']
        p.source = post['source']
        
        p.sample_height = int(post['sample_height'])
        p.sample_width = int(post['sample_width'])
        p.sample = post['sample_url']
        
        p.preview_height = int(post['preview_height'])
        p.preview_width = int(post['preview_width'])
        p.preview = post['preview_url']
        
        stat, _ = Status.get_or_create(value=post['status'])
        p.status = stat

        rat, _ = Rating.get_or_create(value=post['rating'])
        p.rating = rat

        p.score = int(post['score'])
        if post['parent_id']:
            past_posts[id] = p
            p.parent = create_post(get_post(int(post['parent_id'])), past_posts=past_posts)
       
        def insert_tags():
            for tag in post['tags'].split():
                tag_row, _ = Tag.get_or_create(name=tag)
                post_tag = PostTag.get_or_create(post=p, tag=tag_row)
        
        save(p, force_insert=create, on_done=insert_tags)
        
    if and_comments:
        print('Creating comments')
        create_comments(p) 
    if and_notes:
        print('Creating notes')
        create_notes(p)
    if and_download:
        print('Downloading content')
        download(p)
    return p

def download_file(url):
    local_filename = url.split('/')[-1]
    prefix = local_filename[:2]+'/'+local_filename[:4]
    local_filename = prefix + '/' + local_filename
    size = 0
    try:
        os.makedirs(IMAGE_DIR+prefix+'/')
    except FileExistsError:
        pass
    with requests.get(url, stream=True) as r:
        try:
            r.raise_for_status()
        except:
            traceback.print_exc()
            return
        with open(IMAGE_DIR+local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                #if chunk: 
                f.write(chunk)
                size += len(chunk)
    
    return local_filename, size

def download(p):
    print('Downloading content for post', p.id)
    rel_path, size = download_file(p.url)
    content = Content()
    content.post = p
    content.path = rel_path
    content.current_size = content.original_size = size
    save(content, True)

def create_comments(post):
    # the API for comments is broken: the "created_at" time is always the current server time, and it's even in the wrong format.
    # so, we have to parse the page too
    found_comments = True
    offset = 0
    while found_comments:
        found_comments = False
        b = fetch(f'https://{SITE}/index.php?page=post&s=view&id={post.id}&pid={offset}')
        post_xml = fetch(f'https://{SITE}/index.php?page=dapi&s=comment&q=index&post_id={post.id}').findAll('comment')
        comments = [i for i in b.findAll('div') if i.get('id', '').startswith('c')][1:]
        for comment in comments:
            found_comments = True
            strings = list(comment.strings)
            # strings LIKE ['Anonymous', ' ', '>> #3464', 'Posted on 2011-06-28 02:32:38 Score: ', '190', ' (vote ', 'Up', ')\xa0\xa0\xa0(', 'Report as spam', ')', 'Is this the very first image for this site?', 'Hope it can overtake the other boorus someday! :)\n']
            try:
                c_id = int(strings[2].split('#')[-1])
            except ValueError:  # somebody's username is all whitespace (see comment 2 on #8586 (comment #1422504)
                strings = [' ']+strings
                c_id = int(strings[2].split('#')[-1])
            try:
                xml_comment = [i for i in post_xml if i['id']==str(c_id)][0]
            except IndexError:
                # There are some anomalous posts (such as #6 on rule34.xxx) where the API returns no comments even though there are comments in the web interface. We'll ignore these comments.
                print('Weird comments on post #', post.id)
                return None
            try:
                c = Comment.get(Comment.id == c_id)
                create = False
            except Comment.DoesNotExist:
                c = Comment()
                c.id = c_id
                create = True
            if create:
                date = strings[3].split('Posted on ')[1].split(' Score:')[0]
                c.created_at = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                c.post = post
                c.body = xml_comment['body']
                c.author = get_author(xml_comment['creator_id'], xml_comment['creator'])
            c.score = int(strings[4])
            save(c, force_insert=create)
        offset += 10

def create_notes(post):
    notes_xml = fetch(f'https://{SITE}/index.php?page=dapi&s=note&q=index&post_id={post.id}').findAll('note')
    for note in notes_xml:
        try:
            note_row = Note.get_by_id(int(note['id']))
            create = False
        except Note.DoesNotExist:
            note_row = Note()
            note_row.id = int(note['id'])
            create = True
        note_row.created_at = datetime.datetime.strptime(note['created_at'], '%a %b %d %H:%M:%S %z %Y')
        note_row.updated_at = datetime.datetime.strptime(note['updated_at'], '%a %b %d %H:%M:%S %z %Y')
        note_row.is_active = note['is_active']=='true'
        note_row.version = int(note['version'])
        note_row.post = post
        note_row.x = int(note['x'])
        note_row.y = int(note['y'])
        note_row.width = int(note['width'])
        note_row.height = int(note['height'])
        note_row.body = note['body']
        note_row.author = get_author(note['creator_id'])
        save(note_row, force_insert = create)

JOBS = queue.Queue()

def download_single(post_row, content=True):
    post = post_row.id
    print('getting', post)
    result = create_post(get_post(post), and_download=content)
    if result is None:
        print(post, 'is unavailable')
        UnavailablePost.get_or_create(id=post)
    def accept():
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ACCEPTED ID', post)
        post_row.delete_instance()
        try:
            DownloadedPost.create(id=post)
        except:
            try:
                dp = DownloadedPost.get_by_id(post)
                dp.when = datetime.datetime.now()                
                dp.save()
            except:
                pass
    INTO_DB.put((None, None, accept))

if __name__ == '__main__':
    import concurrent.futures
    import threading
#    threading.Thread(target=prefetch).start()
    import tqdm
    print('Putting jobs into queue...')
#    for i in tqdm.tqdm(range(Content.select(Content.post_id).order_by(-Content.id).scalar()-50, 3488797)):
#        JOBS.put(i)
#    for i in db.execute_sql('SELECT post.id FROM post where post.id not in (select content.post_id from content union select unavailablepost.id from unavailablepost);'):
#        print(i)
#        JOBS.put(int(i[0]))
    print(JOBS.qsize())
    def dl():
        while 1:
            try:
                if random.randint(1, 20)==1:
                     post_row = QueuedPost.select().get()
                else:
                    post_row = QueuedPost.select().where(QueuedPost.id >= random.choice(range(1, QueuedPost.select(fn.Max(QueuedPost.id)).scalar()))).get()
            except:
                print('FAILED getting new job')
                traceback.print_exc()
                return
            download_single(post_row)

    for i in range(2):
        threading.Thread(target=dl).start()
    for i in range(6):
        threading.Thread(target=put_into_db).start()
    put_into_db()
