from peewee import *
import datetime
from PIL import Image
import hashlib
import io
Image.MAX_IMAGE_PIXELS = None

SITE = 'rule34.xxx'
IMAGE_DIR = '/hugedata/rule34.xxx/'

#db = SqliteDatabase(SITE+'.db', timeout=600)
db = MySQLDatabase('rule34', user='booru', password='booru', host='10.0.0.2')


#import logging
#logger = logging.getLogger('peewee')
#logger.addHandler(logging.StreamHandler())
#logger.setLevel(logging.DEBUG)

class MyModel(Model):
    class Meta:
        database = db

class AccessLevel(MyModel):
    name = CharField(unique=True)

class User(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    username = CharField(null=True)
    level = ForeignKeyField(AccessLevel, null=True)
    join_date = DateField(null=True)

class Rating(MyModel):
    value = CharField(unique=True)

class Status(MyModel):
    value = CharField(unique=True)

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

class Post(MyModel):
    id = IntegerField(primary_key=True, unique=True)

    width = IntegerField()
    height = IntegerField()
    url = CharField(unique=True)

    sample_width = IntegerField()
    sample_height = IntegerField()
    sample = CharField()

    preview_width = IntegerField()
    preview_height = IntegerField()
    preview = CharField()

    md5 = CharField(unique=True)
    created_at = DateTimeField()
    changed_at = DateTimeField()
    score = IntegerField()
    creator = ForeignKeyField(User)
    rating = ForeignKeyField(Rating)
    status = ForeignKeyField(Status)
    source = CharField()
    
    parent = ForeignKeyField('self', backref='children', null=True)

    def get_thumb(self):
        content = None
        for i in self.content:
            content = i
        if content is None:
            return None, None
        return content.get_thumb( (self.preview_width, self.preview_height) )

class Content(MyModel):
    post = ForeignKeyField(Post, backref='content')
    path = CharField(unique=True)
    original_length = IntegerField()
    current_length = IntegerField()
    
    def is_modified(self):
        return len(self.mods)!=0

    def get_thumb(self, size):
        thumb = None
        for i in self.thumbnail:
            thumb = i
        if thumb is None:
            thumb = Thumbnail.generate_from(self.path, size, self)
        thumb.last_accessed = datetime.datetime.now()
        thumb.save()
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


class Modification(MyModel):
    code = CharField(unique=True, index=True)
    description = TextField()

class ContentModification(MyModel):
    content = ForeignKeyField(Content, backref='mods', index=True)
    mod = ForeignKeyField(Modification, backref='content', index=True)
    additional_data = CharField()
    class Meta:
        primary_key = CompositeKey('content', 'mod')

class PostTag(MyModel):
    tag = ForeignKeyField(Tag, backref='posts')
    post = ForeignKeyField(Post, backref='tags')
    class Meta:
        primary_key = CompositeKey('tag', 'post')

class Comment(MyModel):
    author = ForeignKeyField(User, backref='comments')
    post = ForeignKeyField(Post, backref='comments')
    id = IntegerField(primary_key=True, unique=True)
    body = TextField()
    score = IntegerField()
    created_at = DateTimeField()

class Note(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    author = ForeignKeyField(User, backref='comments')
    post = ForeignKeyField(Post, backref='comments')
    body = TextField()
    created_at = DateTimeField()
    updated_at = DateTimeField()
    is_active = BooleanField()
    version = IntegerField()

    x = IntegerField()
    y = IntegerField()
    width = IntegerField()
    height = IntegerField()

class QueuedPost(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    
class DownloadedPost(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    when = DateTimeField(default=datetime.datetime.now)

db.create_tables([AccessLevel, User, Rating, Status, Tag, Post, PostTag, Comment, Note, Type, TagType, UnavailablePost, Content, ContentModification, Modification, QueuedPost, DownloadedPost, Thumbnail])
