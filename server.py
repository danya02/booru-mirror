from database import *
import download
from flask import Flask, render_template, request, url_for, redirect, send_file
import math
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

    if ' ' in query:
        return 'multiple tags are not supported yet'

    tag = Tag.get(Tag.name==query)
    posttags = PostTag.select().where(PostTag.tag==tag)
    max_page = math.ceil(posttags.count()/ELEM_PER_PAGE)
    if page < 1 or page > max_page:
        return redirect(get_page(1))

    posttags = posttags.paginate(page, ELEM_PER_PAGE)

    posts = []

    for pt in posttags:
        cursor = db.execute_sql('select post.id, GROUP_CONCAT(tag.name) from post inner join posttag on posttag.post_id = post.id inner join tag on posttag.tag_id = tag.id where post.id = %s group by post.id', pt.post_id)
        for row in cursor.fetchall():
            posts.append(row)


    def get_post(id):
        return url_for('view_post', id=id)

    return render_template('search.html', query=query, cur_page=page,  max_page=max_page, posts=posts, get_post=get_post, max=max, min=min, get_url_for_page=get_page)

@app.route('/post/<int:id>')
def view_post(id):
    post = Post.get_or_none(Post.id==id)
    if post is None:
        return 'no such post', 404
    cursor = db.execute_sql('select GROUP_CONCAT(tag.name) from post inner join posttag on posttag.post_id = post.id inner join tag on posttag.tag_id = tag.id where post.id = %s group by post.id', id)
    tags = ''
    for row in cursor.fetchall():
        tags = row[0]
    return render_template('post.html', post=post, tags=tags, unavail=UnavailablePost.get_or_none(UnavailablePost.id==id), content=Content.get_or_none(Content.post_id==id))

@app.route('/post/<int:id>/update')
def update_post(id):
    download.download_single(QueuedPost(id=id))
    download.put_into_db(timeout=1)
    return redirect(url_for('view_post', id=id))


@app.route('/content/<int:id>')
def view_content(id):
    content = Content.get_or_none(Content.id==id)
    if content is None:
        return 'no such content', 404
    return send_file(IMAGE_DIR+content.path)


if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=True)
