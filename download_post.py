from download import get_user, download_post_comments, download_post_notes, get_author
import requests

def get_post(id, skip_download_if_present=True, and_content=True, and_comments=True, and_notes=True, visited=None):
    if visited is None:
        visited = dict()
    elif id in visited:
        return id
    p = Post.get_or_none(Post.id==id)
    if p is not None:
        if skip_download_if_present:
            return p
    else:
        p = Post()
        p.id = id
    r = requests.get('https://konachan.net/post.json', params={'limit':1, 'tags': f'id:{id}'}).json()
    if len(r)==0:
        return None
    r = r[0]
    
    
    p.file_url = r.get('file_url')
    p.width = r['width']
    p.height = r['height']
    
    p.jpeg_url = r.get('jpeg_url')
    p.jpeg_width = r['jpeg_width']
    p.jpeg_height = r['jpeg_height']
    
    p.sample = r.get('sample_url')
    p.sample_width = r['sample_width']
    p.sample_height = r['sample_height']

    p.preview = r.get('preview_url')
    p.preview_width = r['preview_width']
    p.preview_height = r['preview_height']
    p.actual_preview_width = r['actual_preview_width']
    p.actual_preview_height = r['actual_preview_height']


    p.created_at = datetime.datetime.fromtimestamp(r['created_at'])
    p.md5 = r['md5']
    p.score = r['score']
    p.creator = get_author(r['author'], r['creator_id'])
    p.source = r['source']

    p.rating, _ = Rating.get_or_create(value=r['rating'])
    p.status, _ = Status.get_or_create(value=r['status'])

    p.is_held = r['is_held']

    visited.update({p.id: p})
    p.parent = get_post(r['parent_id'], visited=visited)

    try:
        p.save()
    except:
        p.save(force_insert=True)

    for tag_name in r['tags'].split():
        tag_row, _ = Tag.get_or_create(name=tag_name)

    if and_content:
        download_post_content(p)

    if and_comments:
        download_post_comments(p)

    if and_notes:
        download_post_notes(p)

    return p


def download_file(url):
    local_filename = url.split('/')[-1]
    try:
        return local_filename, len(File.get_file_content(local_filename))
    except File.DoesNotExist:
        pass
    with requests.get(url) as r:
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
    rel_path, size = download_file(p.file_url)
    content = Content()
    content.post = p
    content.path = rel_path
    content.current_length = content.original_length = size
    return content

if __name__ == '__main__':
    for i in range(Post.select(fn.Max(Post.id)) or 1, 317257):
        get_post(i)
