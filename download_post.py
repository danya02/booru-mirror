from download_comments import * # download_post_comments
from download_notes import * # download_post_notes
from download_author import * # get_author
import requests
import traceback
import queue_ops

session = requests.session()
session.proxies = {}
#session.proxies['http'] = 'socks5h://localhost:9050'
#session.proxies['https'] = 'socks5h://localhost:9050'

def get_post(id, skip_download_if_present=True, and_content=True, and_comments=True, and_notes=True, visited=None):
    if id is None:
        return None
    if visited is None:
        visited = dict()
    elif id in visited:
        return id
    p = Post.get_or_none(Post.id==id)
    if p is not None:
        print('Post', id, 'exists already')
        if skip_download_if_present:
            print('Skipping download', id)
            return p
    else:
        p = Post()
        p.id = id
    r = session.get('https://' + SITE + '/post.json', params={'limit':1, 'tags': f'id:{id}'}).json()
    if len(r)==0:
        DownloadError.create(entity_id=id, entity_type='post', reason='Lookup by ID failed')
        queue_ops.accept_by_id(id, 'post')
        return None
    r = r[0]
    
    
    p.file_ext = (r.get('file_url').split('.')[-1]) if 'file_url' in r else None
    p.md5 = r['md5']
    p.width = r['width']
    p.height = r['height']
    
    p.jpeg_width = r['jpeg_width']
    p.jpeg_height = r['jpeg_height']
    
    p.sample_width = r['sample_width']
    p.sample_height = r['sample_height']

    p.preview_width = r['preview_width']
    p.preview_height = r['preview_height']
    p.actual_preview_width = r['actual_preview_width']
    p.actual_preview_height = r['actual_preview_height']

    # check if everything downloading
    for i in ['file_url', 'jpeg_url', 'preview_url', 'sample_url']:
        url = getattr(p, i)
        if url is None:
            if i == 'file_url':
                break
            continue
        try:
            request = session.head(url)
            request.raise_for_status()
        except:
            if i=='file_url': # if error on file url, it means post is deleted
                break
            DownloadError.create(entity_id=id, entity_type='post', reason='failed check url '+url+' which is '+i)
            os.abort() # required so invalid data does not get stored up the stack


    p.created_at = datetime.datetime.fromtimestamp(r['created_at'])
    p.score = r['score']
    p.creator = get_author(r['author'], r['creator_id'])
    p.source = r['source']

    p.rating, _ = Rating.get_or_create(value=r['rating'])
    p.status, _ = Status.get_or_create(value=r['status'])

    p.is_held = r['is_held']

    visited.update({p.id: p})
    p.parent = get_post(r['parent_id'], visited=visited)

    try:
        p.save(force_insert=True)
    except IntegrityError:
        p.save()

    for tag_name in r['tags'].split():
        tag_row, _ = Tag.get_or_create(name=tag_name)
        PostTag.get_or_create(post=p, tag=tag_row)

    if 'flag_detail' in r:
        fp = FlaggedPost.get_or_none(post=p) or FlaggedPost()
        fp.post = p
        fp.reason = r['flag_detail']['reason']
        fp.created_at = datetime.datetime.fromisoformat(r['flag_detail']['created_at'][:-1])
        fp.first_detected_at = fp.first_detected_at or datetime.datetime.now()
        try:
            fp.save(force_insert=True)
        except:
            fp.save()

    queue_ops.accept_by_id(id, 'post')

    if and_content:
        download_post_content(p)

    if and_comments:
        download_post_comments(p)

    if and_notes:
        download_post_notes(p)

    return p


def download_file(url):
    local_filename = url.split('/')[-2]  + '.' + url.split('.')[-1]
    try:
        return local_filename, len(File.get_file_content(local_filename))
    except File.DoesNotExist:
        pass
    with session.get(url) as r:
        try:
            r.raise_for_status()
        except:
            traceback.print_exc()
            return
        File.set_file_content(local_filename, r.content)
        return local_filename, len(r.content)

def download_post_content(p):
    if not p.file_url:
        return None
    resp = download_file(p.file_url)
    if resp is None:
        return None
    rel_path, size = resp
    content = Content.get_or_none(Content.path == rel_path) or Content()
    content.post = p
    content.path = rel_path
    content.length = size
    try:
        content.save(force_insert=True)
    except:
        content.save()
    queue_ops.accept_by_id(p.id, 'content')
    return content

if __name__ == '__main__':
    for i in queue_ops.fetch_many('post'):
        print('Downloading post', i.entity_id)
        get_post(i.entity_id, skip_download_if_present=False)
#    for i in Post.select(Post.id).where(Post.file_ext.is_null(True)).iterator():
