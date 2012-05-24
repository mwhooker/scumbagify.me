from __future__ import division
import urllib
import os.path
import json
import tempfile
from contextlib import closing
from PIL import Image

hat = Image.open(os.path.join(os.path.dirname(__file__), '..', "ScumbagSteveHat.png"))

# TODO: turn in to class. remove code dup.


def scumbagify(face, url):
    """Place the hat on the image at `url` and upload to s3.

    returns uploaded public URL."""
    tag = face.faces_detect(url)
    if tag['status'] != 'success':
        raise Exception("Retrieving tags not successful. %s" % tag['status'])


def find_tag(tags):
    """Find the tag that most likely identifies the face."""
    tags = [t for t in tags \
            if 'face' in t['attributes']]
    return max(
        tags,
        key=lambda t: t['attributes']['face']['confidence']
    )


def find_scale(resp):
    """Return (x, y) we think we should scale the hat to."""

    #return hat.size

    assert len(resp['photos']) == 1
    photo = resp['photos'][0]
    tag = find_tag(photo['tags'])
    norm_x = lambda x: int(photo['width'] * (x / 100))

    width = norm_x(tag['width']) * 1.75

    print "hat size, ", hat.size
    print "width: ", width
    print "scale factor: ", width / hat.size[0]
    return map(int, (width, hat.size[1] * (width / hat.size[0])))



def find_coords(resp, hat_size):
    """Find where we should place the hat."""

    assert len(resp['photos']) == 1
    photo = resp['photos'][0]
    tag = find_tag(photo['tags'])
    norm_y = lambda y: int(photo['height'] * (y / 100))
    norm_x = lambda x: int(photo['width'] * (x / 100))

    center_x = norm_x(tag['center']['x'])
    center_y = norm_y(tag['center']['y'] - 10)
    face_height = norm_y(tag['height'])
    return {
        # relative to hat size
        'x': center_x - hat_size[0] / 2,
        # top of hat relative to face
        'y': center_y - face_height
    }


def decorate(im, resp):
    """Decorate an image with face data."""

    photo = resp['photos'][0]
    tag = find_tag(photo['tags'])
    color = (232, 118, 0)
    #red = (0xD0, 0x20, 0x00)#D20
    norm_y = lambda y: int(photo['height'] * (y / 100))
    norm_x = lambda x: int(photo['width'] * (x / 100))

    for t in [i for i in tag if isinstance(tag[i], dict)]:
        if 'x' in tag[t]:
            x = norm_x(tag[t]['x'])
            y = norm_y(tag[t]['y'])
            print "%s: (%s, %s)" % (t, x, y)
            im.putpixel((x, y), color)
            im.putpixel((x, y+1), color)
            im.putpixel((x+1, y), color)
            im.putpixel((x+1, y+1), color)
            #im[x, y] = (0xcc, 0xcc, 0xcc)

    t_height = norm_y(tag['height'])
    center_x = norm_x(tag['center']['x'])
    center_y = norm_y(tag['center']['y'])
    for i in xrange(t_height):
        im.putpixel((center_x, center_y - i), (color))


if __name__ == '__main__':
    with open(os.path.join('..', 'test.json')) as f:
        resp = json.load(f)

    url = resp['photos'][0]['url']
    with closing(urllib.urlopen(url)) as f:
        facef = tempfile.TemporaryFile()
        facef.write(f.read())
    facef.seek(0)
    face = Image.open(facef)

    resize_to = find_scale(resp)
    print "resize to: ", resize_to
    new_hat = hat.resize(resize_to)

    #coords = find_coords(find_tag(resp))
    coords = find_coords(resp, resize_to)
    print "coords: ", coords

    face.paste(new_hat, (int(coords['x']), int(coords['y'])), new_hat)
    #decorate(face, resp)
    face.save('../test.png')