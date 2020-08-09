from PIL import Image
import PIL
from database import *
import traceback
import os

def into_indexed_color(img):
    if 'A' in img.mode or 'a' in img.mode:
        raise ValueError('Alpha channel present in image, cannot index')
    elif 'P' in img.mode:
        raise ValueError('Picture already indexed color')
    palette = img.getcolors()
    if palette is None:
        raise ValueError('More than 256 colors used, cannot index')

    return img.convert('P')

def row_into_indexed_color(content_row):
    mod_row, _ = Modification.get_or_create(code='index_color_lossless', description='Transform image from RGB color into indexed color mode, without losing any detail. Only works if there are less than 256 colors.')
    try:
        img = Image.open(IMAGE_DIR + content_row.path)
    except FileNotFoundError:
#        print('File not found:', IMAGE_DIR + content_row.path)
        return
    except PIL.UnidentifiedImageError as e:
        data = open(IMAGE_DIR + content_row.path, 'rb').read(8192)
        if b'html' in data.lower():
            print(repr(content_row), 'HAS HTML DATA IN FILE!!!')
            content_row.delete_instance()
        elif len(data)<5:
            print(repr(content_row), 'HAS EMPTY FILE!!!')
            content_row.delete_instance()
        else:
            raise e
        return
    try:
        img.seek(1)
        print('More than one frame in image, skipping')
        return
    except EOFError:
        pass
    old_path = IMAGE_DIR + content_row.path
    new_path = IMAGE_DIR + 'modified/'+content_row.path+'.png'
    try:
         os.makedirs('/'.join(new_path.split('/')[:-1]))
    except FileExistsError:
        pass
    try:
        new_img = into_indexed_color(img)
    except:
        traceback.print_exc()
        return
    new_img.save(new_path)
    content_row.path = 'modified/'+content_row.path+'.png'
    content_row.save()
    ContentModification.get_or_create(content=content_row, mod=mod_row)
    os.unlink(old_path)

if __name__ == '__main__':
    last_id = ContentModification.select(ContentModification.content_id).where(ContentModification.mod_id==1).order_by(-ContentModification.content_id).limit(1).scalar()
    for cont in Content.select().where(Content.id > last_id).iterator():
        print('Index color: ', repr(cont))
        try:
            row_into_indexed_color(cont)
        except:
            traceback.print_exc()
            input('ENTER to continue:')
