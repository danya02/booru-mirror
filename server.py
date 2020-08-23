from database import *
import download
from flask import Flask, render_template, request, url_for, redirect, send_file, request, make_response, jsonify
import math
import optimize_img
import base64
import os

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

ELEM_PER_PAGE = 50

@app.route('/search')
def search():
    query = request.args.get('q')
    page = int(request.args.get('p') or 1)
    if not query:
        return redirect(url_for('index'))
    def get_page(num):
        return url_for('search', q=query, p=num)    

    tags = query.split()
    tag_rows = []
    for i in tags:
        tag_rows.append(Tag.get(Tag.name == i))

    posts_query = PostTag.select(PostTag.post_id).where(PostTag.tag == tag_rows[0])
    for tagrow in tag_rows[1:]:
        posts_query = posts_query.intersect(PostTag.select(PostTag.post_id).where(PostTag.tag == tagrow))


    max_page = math.ceil(posts_query.count()/ELEM_PER_PAGE)
    if page < 1 or page > max_page:
        return redirect(get_page(1))

    posts_query = posts_query.paginate(page, ELEM_PER_PAGE)

    post_ids = [posttag.post_id for posttag in posts_query]
    post_tags = dict()


    tag_sep = 'TAGseparator_tagSEPARATOR'
    cursor = db.execute_sql('''SELECT post.id, GROUP_CONCAT(tag.name SEPARATOR %s)
FROM post INNER JOIN posttag ON posttag.post_id = post.id
INNER JOIN tag ON posttag.tag_id = tag.id
WHERE post.id IN ''' + '('+ ', '.join([db.param] * len(post_ids)) + ')' + ''' GROUP BY post.id''', [tag_sep]+post_ids)
    for row in cursor.fetchall():
        id, tags = row
        post_tags[id]=tags.split(tag_sep)

    post_rows = list(Post.raw('''SELECT * FROM post
WHERE post.id IN ''' + '('+ ', '.join([db.param] * len(post_ids)) + ')', *post_ids))


    post_rows.sort(key=lambda x: x.id)
    post_rows_dict = dict()
    for row in post_rows:
        post_rows_dict[row.id]=row

    
    post_list = []
    for id in post_ids:
        post_list.append( (post_rows_dict[id], post_tags[id]) )


    def get_post(id):
        return url_for('view_post', id=id)

    return render_template('search.html', query=query, cur_page=page,  max_page=max_page, posts=post_list, get_post=get_post, max=max, min=min, get_url_for_page=get_page)

@app.route('/post/<int:id>')
def view_post(id):
    post = Post.get_or_none(Post.id==id)
    if post is None:
        post = Post(id=id)
        tags = 'DOES NOT EXIST'
        content = None
        return render_template('post.html', post=post, tags=tags, unavail=UnavailablePost.get_or_none(UnavailablePost.id==id), content=Content.get_or_none(Content.post_id==id))
    cursor = db.execute_sql('select GROUP_CONCAT(tag.name separator ", ") from post inner join posttag on posttag.post_id = post.id inner join tag on posttag.tag_id = tag.id where post.id = %s group by post.id', id)
    tags = ''
    for row in cursor.fetchall():
        tags = row[0]
    return render_template('post.html', post=post, tags=tags, unavail=UnavailablePost.get_or_none(UnavailablePost.id==id), content=Content.get_or_none(Content.post_id==id))

@app.route('/post/<int:id>/update')
def update_post(id):
    download.download_single(QueuedPost(id=id))
    download.put_into_db(timeout=1)
    return redirect(url_for('view_post', id=id))

@app.route('/content/filter/<filter_name>/<int:target_id>')
def preview_filter(filter_name, target_id):
    filter = optimize_img.FILTERS[filter_name]
    target_row = Content.get_by_id(target_id)
    params = request.args
    result_img, add_data = filter(target_row, **params)
    result_size, result_path = optimize_img.get_img_size(result_img, drop_img=False)
    with open(result_path, 'rb') as o:
        data = str(base64.b64encode(o.read()), 'ascii')
    commit_url = url_for('commit_filter', filter_name=filter_name, target_id=target_id, **params)
    os.unlink(result_path)
    return render_template('preview_filter.html', target_row=target_row, params=params, img_data=data, add_data=add_data, commit_url=commit_url, old_size=target_row.current_length, new_size=result_size)

@app.route('/content/filter/commit/<filter_name>/<int:target_id>')
def commit_filter(filter_name, target_id):
    filter = optimize_img.FILTERS[filter_name]
    target_row = Content.get_by_id(target_id)
    params = request.args
    filter(target_row, do_update=True, **params)
    return redirect(url_for('view_content', id=target_id))

@app.route('/content/<int:id>')
def view_content(id):
    content = Content.get_or_none(Content.id==id)
    if content is None:
        return 'no such content', 404
    return send_file(IMAGE_DIR+content.path)

@app.route('/post/<int:id>/thumbnail')
def view_post_thumbnail(id):
    def no_thumb(code):
        # below is 150x150 "red X on white field" PNG image
        data = b'''iVBORw0KGgoAAAANSUhEUgAAAJYAAACWAQMAAAAGz+OhAAAABlBMVEX/AAD///9BHTQRAAAACXBI
        WXMAAC4jAAAuIwF4pT92AAACF0lEQVRIx32WQU7DMBBFXRWpGyQugNQrcAAkrsUCqTlajpIjZJmF
        lWDPjM03edAVfSH2i5uZ+Sml+6GfJdXPy8BmY7eBTcauAzOULop2Z0lZDvYQtgX7ELYGu5/0RsE5
        2O2kNwoGUsGmp4K5s8dJTwXXzu4nPRWcO7v90psGwUqe0qyCpvecFhU0vde0qqDpvadNBe0fvlJW
        QVsop10FbcOcDhU0scJU0K4XJoK+TmEi6PsVJoLuVZgI+uXCRNCXKUwEfbvCRNC1KvsR9KuVdcFY
        pbIuGLtV1gXDqrIuGBcr64KxSGVdMDarrAuGlLEmGNeMxT1tDWN9bd/LWDg0J2Pxpbkbi5vaMxqL
        xdtZGAuJpuTMvzV1Z3ZXf0Rn8erEUTgzi892ZM5M8K0dbU5jRR2d7UM1OusVehU2afEEm7XIgi1a
        jMFWLdpgmxZ3sKxNINiuzSLYoU2lsUlqu7FZekBji/SKxlbpKY1t0nuyVlX/W6rvMrJDet5/jO6l
        PciFnOnZ6AzorOBM6ezpN6Lfkn5zejfoHaJ3Dd5JenfpHadaoJqh2qIapFqFmqbapx5BvYR6DvUm
        6mHU66AnUu+kHku9mHo29XaaATQrYKbQ7KEZRbOMZh7NRpqhNGthJtPsphlPWYAyA2ULyiCUVSjT
        /JV9KCNRlqLMBdmMMhxlPcqElB0pY1IWpcwK2ZYyMGVlytSUvU8Z/Rtr71CzBTdKkgAAAABJRU5E
        rkJggg==
        '''
        data = base64.b64decode(data)
        resp = make_response(data, code)
        resp.mimetype = 'image/png'
        resp.cache_control.public = True
        resp.cache_control.immutable = True
        resp.cache_control.max_age = 60  # short because issue causing absence of thumb may be resolved soon
        return resp
    try:
        post = Post.get_by_id(id)
    except Post.DoesNotExist:
        return no_thumb(404)

    data, type = post.get_thumb()
    if data is None:
        return no_thumb(200)

    resp = make_response(data)
    resp.mimetype = type
    resp.cache_control.public = False  # should be true, but I am currently on an untrusted connection
    resp.cache_control.immutable = True
    resp.cache_control.private = True
    resp.cache_control.max_age = 86400
    return resp

@app.route('/autocomplete')
def autocomplete_tags():
    query = request.args.get('q') or ''
    tags = Tag.select().where(Tag.name % (query+'%')).limit(15)
    resp = []
    for tag in tags:
        resp.append({'label': tag.name, 'value': tag.name}) # TODO: add count of posts with tag
    return jsonify(resp)
    

if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=True)
