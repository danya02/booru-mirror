from peewee import *
import datetime

SITE = 'rule34.xxx'

#db = SqliteDatabase(SITE+'.db', timeout=600)
db = MySQLDatabase('rule34', user='booru', password='booru', host='10.0.0.2')


class MyModel(Model):
    class Meta:
        database = db

class User(MyModel):
    id = IntegerField(primary_key=True, unique=True)
    username = CharField(null=True)

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

class Content(MyModel):
    post = ForeignKeyField(Post, unique=True, backref='content')
    path = CharField(unique=True)
    def is_modified(self):
        return len(self.mods)!=0

class ContentModification(MyModel):
    content = ForeignKeyField(Content, backref='mods', index=True)
    mod = ForeignKeyField(Modification, backref='content', index=True)
    class Meta:
        primary_key = CompositeKey('content', 'mod')

class Modification(MyModel):
    code = CharField(unique=True, index=True)
    description = TextField()

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

db.create_tables([User, Rating, Status, Tag, Post, PostTag, Comment, Note, Type, TagType, UnavailablePost, Content, ContentModification, Modification])
