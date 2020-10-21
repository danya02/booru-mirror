from peewee import *
import datetime
from PIL import Image
import hashlib
import io
import os
Image.MAX_IMAGE_PIXELS = None

SITE = 'konachan.net'
IMAGE_DIR = '/hugedata/booru/konachan.net/'

#db = SqliteDatabase(SITE+'.db', timeout=600)
db = MySQLDatabase('konachan', user='booru', password='booru', host='10.0.0.2')


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
class ForumPost(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    title = TextField(null=True)
    body = TextField()
    updated_at = DateTimeField()
    pages = IntegerField() 

    creator = ForeignKeyField(User, backref='forum_posts')
    parent = ForeignKeyField('self', backref='children', null=True)
    

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

    md5 = CharField(unique=True)
    file_ext = CharField(index=True, null=True)
    
    @property
    def file_url(self):
        if self.file_ext is None:
            return None
        return 'https://' + SITE + '/image/'+self.md5+'/'+str(self.id)+'.'+self.file_ext

    @property
    def jpeg_url(self):
        if self.file_ext == 'jpg' or self.file_ext == 'jpeg':
            return 'https://' + SITE + '/image/'+self.md5+'/'+str(self.id)+'.'+self.file_ext
        return 'https://' + SITE +'/jpeg/'+self.md5+'/'+str(self.id)+'.jpg'

    @property
    def preview_url(self):
        return f'https://' + SITE + f'/data/preview/{self.md5[0:2]}/{self.md5[2:4]}/{self.md5}.jpg'
    
    @property
    def sample_url(self):
        if (self.sample_width, self.sample_height) == (self.width, self.height): return self.jpeg_url
        return f'https://' + SITE + f'/sample/{self.md5}/1.jpg'

    width = IntegerField()
    height = IntegerField()

    sample_width = IntegerField()
    sample_height = IntegerField()

    preview = CharField(unique=True, null=True)
    preview_width = IntegerField()
    preview_height = IntegerField()
    actual_preview_width = IntegerField()
    actual_preview_height = IntegerField()

    created_at = DateTimeField()
    score = IntegerField()
    creator = ForeignKeyField(User, null=True)
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
class DownloadError(MyModel):
    entity_id = IntegerField(index=True)
    entity_type = CharField(index=True)
    reason = CharField(index=True)
    when = DateTimeField(default=datetime.datetime.now, index=True)

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
    score = IntegerField(null=True)
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


@create_table
class QueuedDownload(MyModel):
    entity_id = IntegerField(index=True)
    entity_type = CharField(index=True)
    enqueued_when = DateTimeField(default=datetime.datetime.now)

@create_table
class CompletedDownload(MyModel):
    entity_id = IntegerField(index=True)
    entity_type = CharField(index=True)
    completed_when = DateTimeField(default=datetime.datetime.now)

@create_table
class FlaggedPost(MyModel):
    post = ForeignKeyField(Post, backref='flags', unique=True, primary_key=True)
    reason = CharField(null=True, index=True)
    created_at = DateTimeField(index=True)
    first_detected_at = DateTimeField(index=True, default=datetime.datetime.now)
