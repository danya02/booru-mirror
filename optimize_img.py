from PIL import Image
import PIL
from database import *
import traceback
import os
from functools import wraps
import uuid
import io

FILTERS = dict()

def get_img_size(image, drop_img=True):
    try:
        os.makedirs(IMAGE_DIR + 'optimize-test/')
    except FileExistsError:
        pass
    path = IMAGE_DIR + 'optimize-test/' + str(uuid.uuid4()) + '.png'
    image.save(path)
    size = os.path.getsize(path)
    if drop_img:
        os.unlink(path)
    return (size, path) if not drop_img else size

def filter(code, description):
    def wrapper(func):
        @wraps(func)
        def wrapped(target_row, do_update=False, **additional_params):
            mod_row, _ = Modification.get_or_create(code=code, description=description)
            target_img = Image.open(IMAGE_DIR + target_row.path)
            try:
                target_img.seek(1)
                raise TypeError('Image has more than one frame, not continuing')
            except EOFError:
                pass
            result_img, additional_data = func(target_img, target_row=target_row, mod_row=mod_row, **additional_params)
            if do_update:
                old_path = target_row.path
                new_path = 'modified/'+target_row.path+'.png'
                try:
                    os.makedirs('/'+('/'.join(
                        (IMAGE_DIR + new_path).split('/')[:-1])))
                except FileExistsError:
                    pass
                with db.atomic():
                    result_img.save(IMAGE_DIR + new_path)
                    target_row.path = new_path
                    target_row.current_length = os.path.getsize(IMAGE_DIR + new_path)
                    target_row.save()
                    ContentModification.create(content=target_row, mod=mod_row, additional_data=additional_data)
                os.unlink(IMAGE_DIR + old_path)
            else:
               return result_img, additional_data
        FILTERS[code] = wrapped
        return wrapped
    return wrapper

@filter('overlay', 'This image is an alternate form of another image, so it is stored as a difference on the disk. The image on which this one should be overlayed can be found here:')
def into_overlay(alt_img, orig_row_id=None, mod_row=None, **kwargs):
    if orig_row_id is None:
        raise ValueError('No original row ID provided')
    orig_row = Content.get_by_id(orig_row_id)
    orig_img = Image.open(IMAGE_DIR + orig_row.path)
    if alt_img.width != orig_img.width or alt_img.height != orig_img.height:
        raise ValueError('Image size does not match, cannot continue')
    diff_img = Image.new('RGBA', (orig_img.width, orig_img.height), color=(0, 0, 0, 0))
    for y in range(orig_img.height):
        for x in range(orig_img.width):
            new_color = alt_img.getpixel((x,y))
            if orig_img.getpixel((x,y)) != new_color:
                diff_img.putpixel((x,y), tuple(list(new_color)+[255]))

    return diff_img, str(orig_row_id) 


@filter('replace-with-sample', 'The original form of this image has been replaced with the sample form in order to save disk space. Detail may have been lost. You can access the original image at:')
def replace_with_sample(target_img, target_row=None, **kwargs):
    post = Post.get(Post.id = target_row.post_id)
    with requests.get(post.sample_url) as req:
        data = req.content
    fp = io.BytesIO(data)
    result_img = Image.open(fp)
    return result_img, post.url



#if __name__ == '__main__':
#    last_id = ContentModification.select(ContentModification.content_id).where(ContentModification.mod_id==1).order_by(-ContentModification.content_id).limit(1).scalar()
#    for cont in Content.select().where(Content.id > last_id).iterator():
#        print('Index color: ', repr(cont))
#        try:
#            row_into_indexed_color(cont)
#        except:
#            traceback.print_exc()
#            input('ENTER to continue:')
