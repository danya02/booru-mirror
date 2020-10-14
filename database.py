from peewee import *
import datetime
from PIL import Image
import hashlib
import io
import os
Image.MAX_IMAGE_PIXELS = None

SITE = 'rule34.xxx'
IMAGE_DIR = '/hugedata/booru/rule34.xxx/'

#db = SqliteDatabase(SITE+'.db', timeout=600)
db = MySQLDatabase('rule34', user='booru', password='booru', host='10.0.0.2')

def get_post_url_on_source(id):
    return 'https://rule34.xxx/index.php?page=post&s=view&id='+str(id)

content_databases = dict()

def get_content_db(name):
    database = content_databases.get(name[:2])
    if database is None:
        try:
            os.makedirs(IMAGE_DIR+name[:1]+'/')
        except FileExistsError:
            pass
        database = SqliteDatabase(IMAGE_DIR+name[:1]+'/'+name[:2]+'.db', timeout=300)
        content_databases[name[:2]] = database
    return database

class File(Model):
    name = CharField(unique=True, primary_key=True)
    content = BlobField()


    @staticmethod
    def get_file_content(name):
        database = get_content_db(name)
        with database.bind_ctx((File,)):
            database.create_tables((File,))
            return File.get(File.name==name).content

    @staticmethod
    def set_file_content(name, data):
        database = get_content_db(name)
        with database.bind_ctx((File,)):
            database.create_tables((File,))
            try:
                filerow = File.get(File.name == name)
                filerow.content = data
            except File.DoesNotExist:
                filerow = File.create(name=name, content=data)

    @staticmethod
    def delete_file(name):
        database = get_content_db(name)
        with database.bind_ctx((File,)):
            database.create_tables((File,))
            return File.delete().where(File.name==name).execute()


    @staticmethod
    def get_length(name):
        database = get_content_db(name)
        with database.bind_ctx((File,)):
            database.create_tables((File,))
            try:
                return File.select(fn.length(File.content)).where(File.name == name).scalar()
            except File.DoesNotExist:
                return None


import logging
logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
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
        full_img = io.BytesIO(File.get_file_content(path))
        img = Image.open(full_img)
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
class WeirdComment(MyModel):
    post_id=IntegerField()

db.create_tables([AccessLevel, User, Rating, Status, Tag, Post, PostTag, Comment, Note, Type, TagType, UnavailablePost, Content, ContentModification, Modification, QueuedPost, DownloadedPost, Thumbnail])
