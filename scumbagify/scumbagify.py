from __future__ import division
import json
import math
import os.path
import tempfile
import urllib
from contextlib import closing
from itertools import ifilter
from numpy import matrix, array
from PIL import Image, ImageDraw

hat = Image.open(os.path.join(os.path.dirname(__file__), '..', "ScumbagSteveHat.png"))

STEVE_ROLL = -0.218689755275
HAT_LEFT_MARGIN = 15
HAT_TOP_MARGIN = 6
# TODO: scale by resize
HAT_MARGIN = matrix([15, 6])


class FaceNotFound(Exception): pass


def find_tag(tags):
    """Find the tag that most likely identifies the face."""

    tags = [t for t in tags \
            if 'face' in t['attributes']]
    return max(
        tags,
        key=lambda t: t['attributes']['face']['confidence']
    )


def tag_filter(tag):
    """Is this person a scumbag?"""

    return all([
        abs(tag['yaw']) < 15,
        abs(tag['pitch']) < 15
    ])


def scumbagify(im, resp, debug=False):
    """Scumbagify all the faces in the image."""

    assert len(resp['photos']) == 1

    photo = resp['photos'][0]
    failed = True
    for tag in ifilter(tag_filter, photo['tags']):
        face = Face(photo, tag)
        face.scumbagify(im)
        if debug:
            face.decorate(im)
        failed = False

    if failed:
        raise FaceNotFound


class Face(object):

    def __init__(self, photo, tag):
        self.photo = photo
        self.tag = tag
        print "tagid: ", self.tag['tid']

        # all positions are in [0, 100]
        self.norm_y = lambda y: int(self.photo['height'] * (y / 100))
        self.norm_x = lambda x: int(self.photo['width'] * (x / 100))

        # handy attributes
        self.face = {
            'center': (
                self.norm_x(self.tag['center']['x']),
                self.norm_y(self.tag['center']['y'])
            ),
            'height': self.norm_y(self.tag['height']),
            'width': self.norm_x(self.tag['width']),
            'roll': math.radians(self.tag['roll'])
        }

        self.matrices = {
            'center': matrix(self.face['center']),
            # bounding box. clockwise from upper left.
            'bbox': array([
                [[-self.face['width']], [-self.face['height']]],
                [[self.face['width']], [-self.face['height']]],
                [[self.face['width']], [self.face['height']]],
                [[-self.face['width']], [self.face['height']]],
            ]),
            'rotation': matrix([
                [math.cos(self.face['roll']), -math.sin(self.face['roll'])],
                [math.sin(self.face['roll']), math.cos(self.face['roll'])]]
            )
        }


    def find_rotation(self):
        """Return degrees to rotate hat. Accounts for ss calibration."""

        return math.degrees(-abs(STEVE_ROLL - self.face['roll']))


    def find_scale(self):
        """Return (x, y) size we think we should scale the hat to."""

        width = self.face['width'] * 2

        print "hat size, ", hat.size
        print "width: ", width
        print "scale factor: ", width / hat.size[0]
        return map(int, (width, hat.size[1] * (width / hat.size[0])))


    def find_coords(self, hat_size):
        """Find where we should place the hat."""

        top = self.matrices['rotation']
        # about the middle of the forehead
        top = top * matrix([[0], [-self.face['height'] * .75]])
        # position over center of face
        top = top + self.matrices['center'].getT()
        # try to get the middle of the hat in the middle of the forehead
        top = top - matrix(hat_size).getT() / 2
       
        return tuple(map(int, top.getA1()))


    def decorate(self, im):
        """Decorate an image with face data."""

        color = (232, 118, 0)
        red = (0xD0, 0x20, 0x00)#D20
        draw = ImageDraw.Draw(im)

        # draw a box around the face
        box = self.matrices['rotation'].dot(self.matrices['bbox']).getT() + self.matrices['center']
        draw.polygon(map(int, box.getA1()))

        # line over face, oriented for roll
        top = self.matrices['rotation'] * matrix([
            [0], [-self.face['height']]
        ]) + self.matrices['center'].getT()
        bottom = self.matrices['rotation'] * matrix([
            [0], [self.face['height']]
        ]) + self.matrices['center'].getT()
        draw.line([tuple(top.getA1()), tuple(bottom.getA1())], fill=red)

        # vertical line from center to top of face
        center_x, center_y = self.face['center']
        draw.line([(center_x, center_y), (center_x, center_y - self.face['height'])],
                  fill=color)

        # Draw a 4 pixel box over points of interest.
        for t in [i for i in self.tag if isinstance(self.tag[i], dict)]:
            if 'x' in self.tag[t]:
                x = self.norm_x(self.tag[t]['x'])
                y = self.norm_y(self.tag[t]['y'])
                print "putpixel %s: (%s, %s)" % (t, x, y)
                im.putpixel((x, y), color)
                im.putpixel((x, y+1), color)
                im.putpixel((x+1, y), color)
                im.putpixel((x+1, y+1), color)


    def scumbagify(self, im):

        rotation = self.find_rotation()
        print "rotation: ", rotation
        new_hat = hat.rotate(rotation)

        resize_to = self.find_scale()
        print "resize to: ", resize_to
        new_hat = new_hat.resize(resize_to, Image.ANTIALIAS)

        coords = self.find_coords(resize_to)
        print "coords: ", coords

        im.paste(new_hat, coords, new_hat)
        return im


if __name__ == '__main__':
    with open(os.path.join('..', 'daniel.json')) as f:
        resp = json.load(f)

    url = resp['photos'][0]['url']
    with closing(urllib.urlopen(url)) as f:
        imgf = tempfile.TemporaryFile()
        imgf.write(f.read())
    imgf.seek(0)
    img = Image.open(imgf)
    scumbagify(img, resp)
    img.save('../test.png')
