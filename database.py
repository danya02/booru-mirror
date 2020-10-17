from peewee import *
import datetime
from PIL import Image
import hashlib
import io
Image.MAX_IMAGE_PIXELS = None

SITE = 'konachan.net'
IMAGE_DIR = '/hugedata/booru/konachan.net/'

#db = SqliteDatabase(SITE+'.db', timeout=600)
db = MySQLDatabase('konachan', user='booru', password='booru', host='10.0.0.2')


import logging
logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

class MyModel(Model):
    class Meta:
        database = db

def create_table(cls):
    db.create_tables([cls])
    return cls

@create_table
class User(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    username = CharField(null=True)
    profile_picture = BlobField(null=True)
    profile_picture_mimetype = CharField(null=True)
    profile_picture_fetched_at = DateTimeField(null=True)

@create_table
class TempBlacklistedTags(MyModel):
    user = ForeignKeyField(User)
    content = CharField()

@create_table
class Rating(MyModel):
    value = CharField(unique=True)

@create_table
class Status(MyModel):
    value = CharField(unique=True)

@create_table
class Tag(MyModel):
    name = CharField(unique=True)

class Type(MyModel):
    name = CharField(unique=True)

class TagType(MyModel):
    tag = ForeignKeyField(Tag)
    type = ForeignKeyField(Type)
    class Meta:
        primary_key = CompositeKey('tag', 'type')

class UnavailablePost(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    reason = TextField(null=True)
    first_detected_at = DateTimeField(default=datetime.datetime.now)

@create_table
class Post(MyModel):
    id = IntegerField(primary_key=True, unique=True)

    file_url = CharField(unique=True, null=True)
    md5 = CharField(unique=True)
    
    jpeg_url = CharField(unique=True, null=True)
    width = IntegerField()
    height = IntegerField()

    sample = CharField(unique=True, null=True)
    sample_width = IntegerField()
    sample_height = IntegerField()

    preview = CharField(unique=True, null=True)
    preview_width = IntegerField()
    preview_height = IntegerField()
    actual_preview_width = IntegerField()
    actual_preview_height = IntegerField()

    created_at = DateTimeField()
    score = IntegerField()
    creator = ForeignKeyField(User)
    rating = ForeignKeyField(Rating)
    status = ForeignKeyField(Status)
    source = CharField()
    
    is_held = BooleanField()

    parent = ForeignKeyField('self', backref='children', null=True)

    def get_thumb(self):
        content = None
        for i in self.content:
            content = i
        if content is None:
            return None, None
        return content.get_thumb( (self.preview_width, self.preview_height) )

@create_table
class Content(MyModel):
    post = ForeignKeyField(Post, backref='content')
    path = CharField(unique=True)
    length = IntegerField()
    
    def get_thumb(self, size):
        thumb = None
        for i in self.thumbnail:
            thumb = i
        if thumb is None:
            thumb = Thumbnail.generate_from(self.path, size, self)
        thumb.last_accessed = datetime.datetime.now()
        thumb.save(only=[Thumbnail.last_accessed])
        return thumb.data, thumb.content_type


class Thumbnail(MyModel):
    content = ForeignKeyField(Content, backref='thumbnail')
    data = BlobField()
    etag = FixedCharField(max_length=64)
    content_type = CharField()
    last_accessed = DateTimeField(index=True, default=datetime.datetime.now)

    @classmethod
    def generate_from(cls, path, size, content):
        img = Image.open(IMAGE_DIR+path)
        img.thumbnail(size)
        img = img.convert('RGB')
        fp = io.BytesIO()
        img.save(fp, format='JPEG')

        data = fp.getvalue()
        etag = hashlib.sha256(data).hexdigest()
        row = cls.create(content_type='image/jpeg', content=content, data=data, etag=etag)
        #row.save(force_insert=True)
        return row


@create_table
class PostTag(MyModel):
    tag = ForeignKeyField(Tag, backref='posts')
    post = ForeignKeyField(Post, backref='tags')
    class Meta:
        primary_key = CompositeKey('tag', 'post')

@create_table
class Comment(MyModel):
    author = ForeignKeyField(User, backref='comments')
    post = ForeignKeyField(Post, backref='comments')
    id = IntegerField(primary_key=True, unique=True)
    body = TextField()
    score = IntegerField()
    created_at = DateTimeField()
    last_updated = DateTimeField(default=datetime.datetime.now)

@create_table
class Note(MyModel):
    id = IntegerField()
    version = IntegerField()
    author = ForeignKeyField(User, backref='notes')
    post = ForeignKeyField(Post, backref='notes')
    body = TextField()
    created_at = DateTimeField()
    updated_at = DateTimeField()
    is_active = BooleanField()

    x = IntegerField()
    y = IntegerField()
    width = IntegerField()
    height = IntegerField()
    class Meta:
        primary_key = CompositeKey('id', 'version')

class QueuedPost(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    
class DownloadedPost(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    when = DateTimeField(default=datetime.datetime.now)

