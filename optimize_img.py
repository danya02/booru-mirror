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

def rows_into_overlays(orig_row, alt_row):
    mod_row, _ = Modification.get_or_create(code='overlay', description='This image is an alternate form of another image, so it is stored as a difference on the disk. The image on which this one should be overlayed can be found here:')
    orig_img = Image.open(IMAGE_DIR + orig_row.path)
    alt_img = Image.open(IMAGE_DIR + alt_row.path)
    print(orig_row.path, alt_row.path)
    input('Check path!')
    if alt_img.width != orig_img.width or alt_img.height != orig_img.height:
        raise ValueError('Image size does not match, cannot continue')
    diff_img = Image.new('RGBA', (orig_img.width, orig_img.height), color=(0, 0, 0, 0))
    for y in range(orig_img.height):
        for x in range(orig_img.width):
            new_color = alt_img.getpixel((x,y))
            if orig_img.getpixel((x,y)) != new_color:
                diff_img.putpixel((x,y), tuple(list(new_color)+[255]))

    old_path = IMAGE_DIR + alt_row.path
    new_path = IMAGE_DIR + 'modified/'+alt_row.path+'.png'
    try:
         os.makedirs('/'.join(new_path.split('/')[:-1]))
    except FileExistsError:
        pass
    diff_img.save(new_path)
    orig_img.save('/tmp/orig.png')
    alt_img.save('/tmp/alt.png')
    diff_img.save('/tmp/test.png')
    input('Read file now!')
    with db.atomic():
        ContentModification.create(content=alt_row, mod=mod_row, additional_data=str(orig_row.id))
        alt_row.path = 'modified/'+alt_row.path+'.png'
        alt_row.current_length = os.path.getsize(new_path)
        alt_row.save()
        print('alt_row.current_length', alt_row.current_length)
        print('alt_row.original_length', alt_row.original_length)
        
        input('Check size!')
    os.unlink(old_path)
    


    

#if __name__ == '__main__':
#    last_id = ContentModification.select(ContentModification.content_id).where(ContentModification.mod_id==1).order_by(-ContentModification.content_id).limit(1).scalar()
#    for cont in Content.select().where(Content.id > last_id).iterator():
#        print('Index color: ', repr(cont))
#        try:
#            row_into_indexed_color(cont)
#        except:
#            traceback.print_exc()
#            input('ENTER to continue:')
