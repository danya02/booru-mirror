from database import *
import download
from flask import Flask, render_template, request, url_for, redirect, send_file, request, make_response, jsonify, Response
import math
import optimize_img
import base64
import os

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

ELEM_PER_PAGE = 50

def get_post_counts_by_tag(all_tags):
    tag_counts = dict()
    tag_counts_cursor = db.execute_sql('''SELECT tag.name, COUNT(posttag.post_id)
FROM tag INNER JOIN posttag ON posttag.tag_id = tag.id
WHERE tag.id IN ''' + '(' + ', '.join([db.param] * len(all_tags)) + ''') 
GROUP BY tag.id''', list(all_tags))
    for tag_name, post_count in tag_counts_cursor.fetchall():
        tag_counts[tag_name] = post_count
    return tag_counts

@app.route('/search')
def search():
    args = request.args.to_dict(flat=False)
    queries = args['q']
    queries = [i for i in queries if i]
    def get_page(num, **kwargs):
        return url_for('search', q=queries, p=num, **kwargs)
    return search_internal('search.html', get_page)

@app.route('/dedup/')
def find_dedup():
    args = request.args.to_dict(flat=False)
    queries = args.get('q') or []
    queries = [i for i in queries if i]
    base_id = request.args.get('base')
    if base_id:
        base_post = Post.get_by_id(base_id)
    else:
        base_post = None
    def get_page(num, **kwargs):
        return url_for('find_dedup', q=queries, p=num, **kwargs, base=base_id)
    return search_internal('find-dedup.html', get_page, base_post=base_post,
            query_postprocess=lambda x: x.except_(Post.select(Post.id).join(Content).join(ContentModification).join(Modification).where(Modification.code != 'overlay')))

@app.route('/dedup/<int:base>/<int:leaf>')
def run_dedup(base, leaf):
    base = Post.select(Post.id, Content.id).join(Content).where(Post.id==base).get()
    leaf = Post.select(Post.id, Content.id).join(Content).where(Post.id==leaf).get()
    base = base.content
    leaf = leaf.content
    return redirect(url_for('preview_filter', filter_name='overlay', target_id=leaf.id, orig_row_id=base.id))

def search_internal(template_name, get_page, query_postprocess=None, **kwargs):
    args = request.args.to_dict(flat=False)
    queries = args.get('q') or []
    adv_mode = bool(args.get('adv_mode'))
    page = int(request.args.get('p') or 1)

    query_tag_ids = set()
    ambiguous_tags = []

    def generate_db_select(query):
        # analyze query
        tags = query.split()
        tag_rows = []
        for i in tags:
            if i[0] == '-':
                tag = i[1:]
                invert = True
            else:
                tag = i
                invert = False

        
            cnt = len(Tag.select().where(Tag.name == tag))
            if cnt==0:
                return render_template('search.html', query=query, cur_page=1, max_page=1, posts=[], get_post=lambda x: 'http://WTF/'+str(x), max=max, min=min, get_url_for_page=lambda x: 'http://WTF/page/'+str(x), tag_post_counts=dict(), tag_not_found=tag)
            else:
                exact_tag = Tag.get(SQL('BINARY t1.name = %s', [tag]))
                query_tag_ids.add(exact_tag.id)
                if cnt>1:
                    tag_alternates = []
                    for opt in Tag.select().where(Tag.name==tag):
                        print(opt, opt.name)
                        tag_alternates.append(opt.name)
                    ambiguous_tags.append((tag, tag_alternates))
                tag_rows.append((exact_tag, invert))

        # build SQL query

        pos_tags = []
        neg_tags = []
        for tag, invert in tag_rows:
            if invert:
                neg_tags.append(tag)
            else:
                pos_tags.append(tag)
    
        if len(pos_tags)>0:
            # first, create select by first positive statement
            posts_query = PostTag.select(PostTag.post_id.distinct()).where(PostTag.tag == pos_tags[0])
            # then intersect it with other positive statements
            for pos_tag in pos_tags[1:]:
                posts_query = posts_query.intersect( PostTag.select(PostTag.post_id.distinct()).where(PostTag.tag == pos_tag) )
            # and except the negative statements
            for neg_tag in neg_tags:
                posts_query = posts_query.except_( PostTag.select(PostTag.post_id.distinct()).where(PostTag.tag == neg_tag) ) 
        else:
            if len(neg_tags)==0:
                # if not looking for anything particular, just select all posts with tags
                posts_query = PostTag.select(PostTag.post_id.distinct())
            else:
                # it is not optimal to use except against full result set, so instead the query will be a NOT IN:
                posts_query = PostTag.select(PostTag.post_id.distinct()).where(PostTag.tag.not_in(neg_tags))
        return posts_query

    posts_query = None

    for q in queries:
        q = q.strip()
        if q: # so empty queries do not add an unnecessary unlimited select
            sql_q = generate_db_select(q)
            if posts_query is None:
                posts_query = sql_q
            else:
                posts_query = posts_query.union(sql_q)

    if posts_query is None:
        posts_query = PostTag.select(PostTag.post_id)

    if query_postprocess:
        posts_query = query_postprocess(posts_query)


    cnt = posts_query.count()
    max_page = math.ceil(cnt/ELEM_PER_PAGE)
    if page < 1 or page > max_page:
        if cnt != 0:
            return redirect(get_page(1))
        else:
            return render_template(template_name, query=queries, cur_page=1, max_page=1, posts=[], get_post=None, max=max, min=min, get_url_for_page=None, tag_post_counts=dict(), ambiguous_tags=ambiguous_tags, **kwargs)

    # get list of posts to display on this page
    posts_query = posts_query.paginate(page, ELEM_PER_PAGE)

    post_ids = [posttag[0] for posttag in posts_query.tuples()]
    post_tags = dict()


    # for each post, get list of tags belonging to this post
    tag_sep = 'TAGseparator_tagSEPARATOR'
    post_tags_cursor = db.execute_sql('''SELECT post.id, GROUP_CONCAT(tag.id SEPARATOR " "), GROUP_CONCAT(tag.name SEPARATOR %s)
FROM post INNER JOIN posttag ON posttag.post_id = post.id
INNER JOIN tag ON posttag.tag_id = tag.id
WHERE post.id IN ''' + '('+ ', '.join([db.param] * len(post_ids)) + ')' + ''' GROUP BY post.id''', [tag_sep]+post_ids)
    for row in post_tags_cursor.fetchall():
        id, tag_ids, tag_names = row
        post_tags[id] = list(zip(
            list(map(int, tag_ids.split())),
            tag_names.split(tag_sep)))

    # get list of post instances
    post_rows = list(Post.select().join(Rating).where(Post.id.in_(post_ids)))

    post_rows.sort(key=lambda x: x.id)
    post_rows_dict = dict()
    for row in post_rows:
        post_rows_dict[row.id]=row

    # join post instances and tag lists
    post_list = []
    for id in post_ids:
        post_list.append( (post_rows_dict[id], post_tags[id]) )


    # from tag lists, get tags 
    all_tags = set()
    for index, id in enumerate(post_tags):
        for i in query_tag_ids:
            all_tags.discard(i)
        if len(all_tags) > 50:
            break
        for tag in post_tags[id]:
            all_tags.add(tag[0])
            if len(all_tags) > 50:
                break

    # and get count of posts for each of the tags
    # tag_post_counts = get_post_counts_by_tag(all_tags) # FIXME: this takes too long on my system -- why?
    tag_post_counts = dict()
    for i in Tag.select(Tag.name).where(Tag.id.in_(list(all_tags))).tuples():
        tag_post_counts[ i[0] ] = 0
    


    def get_post(id):
        return url_for('view_post', id=id)


    return render_template(template_name, query=queries, cur_page=page, max_page=max_page, posts=post_list, get_post=get_post, max=max, min=min, get_url_for_page=get_page, tag_post_counts=tag_post_counts, ambiguous_tags=ambiguous_tags, advanced_mode=adv_mode, **kwargs)


@app.route('/post/<int:id>')
def view_post(id):
    post = Post.get_or_none(Post.id==id)
    if post is None:
        post = Post(id=id)
        content = None
        return render_template('post.html', post=post, tags=['Post does not exist, consider updating'], tag_counts=dict(), unavail=UnavailablePost.get_or_none(UnavailablePost.id==id), content=Content.get_or_none(Content.post_id==id))
    
    tag_sep = 'TAGseparator_tagSEPARATOR'
    cursor = db.execute_sql('''SELECT GROUP_CONCAT(tag.name SEPARATOR %s) 
FROM post INNER JOIN posttag ON posttag.post_id = post.id INNER JOIN tag ON posttag.tag_id = tag.id 
WHERE post.id = %s GROUP BY post.id''', [tag_sep, id])
    tags = ''
    for row in cursor.fetchall():
        tags = row[0].split(tag_sep)
    tag_counts = get_post_counts_by_tag(tags)
    content = Content.get_or_none(Content.post_id==id)
    mods = []
    base_img = None
    if content:
        for cm in ContentModification.select().join(Modification).where(ContentModification.content == content):
            mods.append((cm.mod.code, cm.mod.description, cm.additional_data))
            if cm.mod.code == 'overlay':
                base_img = Content.get_by_id(int(cm.additional_data))
    return render_template('post.html', post=post, tags=tags, base_img=base_img, tag_counts=tag_counts, modifications=mods, unavail=UnavailablePost.get_or_none(UnavailablePost.id==id), content=content)


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
    return Response(File.get_file_content(content.path), mimetype='image/*')

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
        resp.cache_control.max_age = 86400
        return resp
    def unknown_thumb(code):
        # below is 150x150 "magenta ? on white field" PNG image
        data = b'''iVBORw0KGgoAAAANSUhEUgAAAJYAAACWAQMAAAAGz+OhAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9
        kT1Iw0AcxV9bpUVaHSwo4pChOlkQFXHUKhShQqgVWnUwufQLmjQkKS6OgmvBwY/FqoOLs64OroIg
        +AHi5Oik6CIl/i8ptIjx4Lgf7+497t4B/kaFqWbXOKBqlpFOJoRsblUIviKEAUTQi7DETH1OFFPw
        HF/38PH1Ls6zvM/9OSJK3mSATyCeZbphEW8QT29aOud94igrSQrxOfGYQRckfuS67PIb56LDfp4Z
        NTLpeeIosVDsYLmDWclQiaeIY4qqUb4/67LCeYuzWqmx1j35C8N5bWWZ6zSHkcQiliBCgIwayqjA
        QpxWjRQTadpPePiHHL9ILplcZTByLKAKFZLjB/+D392ahckJNymcALpfbPtjBAjuAs26bX8f23bz
        BAg8A1da219tADOfpNfbWuwI6NsGLq7bmrwHXO4Ag0+6ZEiOFKDpLxSA9zP6phzQfwv0rLm9tfZx
        +gBkqKvUDXBwCIwWKXvd492hzt7+PdPq7wcZZ3KD4Jfq6QAAAAZQTFRF/wD/////nxgy4AAAAAlw
        SFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+QIFw0SHa+VWIoAAAAZdEVYdENvbW1lbnQAQ3JlYXRl
        ZCB3aXRoIEdJTVBXgQ4XAAABVUlEQVRIx+3VMa7DIAwAUEcZMnIEjsLR4GgcJUdgZIjob4ltjEPa
        qOrwpTZLpKcktoMxcDtcGzyzBAfLAKDtTrD09niMHiSL1WxnlfBltG03kJbQvLCIZoUFNCMMCeZm
        FAKmZpkMmiU2z7ayObbIZtkCm2FjqhWfWmk2k23NpmeW94gBC6mW9gqythlDebQVkwjKLJZIFrH4
        db+zefyuNPq1ZAF/urKZlsWiUVeU12bO7NascOe9Z+5Ne1Q6sLZxPmnlxJyy7aLlE/PK0sBW0Wt0
        xYEF0buiNG1F7gWR8qIsDyx1e7ClYpWFbk+3+eR72/oZwWEnZamfORx2URbUvKKwrrei559MRVim
        sN0cVzMWF8goi9zBzQKFFXac7dVmZeV4LtSUzcDs4JxxA/PK0uA8SrgY0lZO76Ut2uLYzEWz2sLn
        zV06z382NBis28++z/5rn/4BxaaJMuHWJqYAAAAASUVORK5CYII=
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
        return unknown_thumb(200)

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
