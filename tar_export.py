from database import *
from flask import Flask, Response
import tarfile

app = Flask(__name__)

@app.route('/<tag>.tar')
def find_by_tag(tag):
    tag = Tag.get(Tag.name == tag)
    explicit = Rating.get(Rating.value == 'e')
    query = Content.select().join(Post).join(PostTag).where(PostTag.tag == tag).where(Post.rating!=explicit).iterator()
    def posts_iterator():
        for content in query:
            data = File.get_file_content(content.path)
            header = tarfile.TarInfo()
            name = f'{content.post_id}-{content.post.rating.value}.{content.path.split(".")[-1]}'
            header.name=name
            header.uid = 1000
            header.gid = 1000
            header.size = len(data)
            header.mtime = content.post.created_at.timestamp()
            yield header.tobuf()
            while len(data)%512 != 0:
                data += b'\x00'*(512 - len(data)%512)
            yield data
        yield b'\0'*1024
    return Response(posts_iterator(), mimetype='application/tar')

if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=True)
