from __future__ import division
import urllib
import os.path
import json
import tempfile
import math
from contextlib import closing
from numpy import matrix, array
from PIL import Image, ImageDraw

hat = Image.open(os.path.join(os.path.dirname(__file__), '..', "ScumbagSteveHat.png"))

STEVE_ROLL = -0.218689755275
HAT_LEFT_MARGIN = 15
HAT_TOP_MARGIN = 6
# TODO: scale by resize
HAT_MARGIN = matrix([15, 6])

# TODO: turn in to class. remove code dup.
# correct for face roll
    # move along x (DONE)
    # rotate to match ss roll.
# more intelligent find_tag method. weight for middle


class Face(object):

    def __init__(self, resp):
        assert len(resp['photos']) == 1
        self.resp = resp
        self.photo = resp['photos'][0]
        self.tag = self.find_tag(self.photo['tags'])
        self.norm_y = lambda y: int(self.photo['height'] * (y / 100))
        self.norm_x = lambda x: int(self.photo['width'] * (x / 100))


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
        

        print self.matrices


    def find_tag(self, tags):
        """Find the tag that most likely identifies the face."""
        tags = [t for t in tags \
                if 'face' in t['attributes']]
        return max(
            tags,
            key=lambda t: t['attributes']['face']['confidence']
        )

    def find_rotation(self):
        """Return degrees to rotate hat, accounting for ss calibration."""

        return math.degrees(-abs(STEVE_ROLL - self.face['roll']))


    def find_scale(self):
        """Return (x, y) we think we should scale the hat to."""

        width = self.face['width'] * 2

        print "hat size, ", hat.size
        print "width: ", width
        print "scale factor: ", width / hat.size[0]
        return map(int, (width, hat.size[1] * (width / hat.size[0])))


    def find_coords(self, hat_size):
        """Find where we should place the hat."""

        top = self.matrices['rotation'] * matrix([
            [0], [-self.face['height'] * .75]
        ]) + self.matrices['center'].getT() - (matrix(hat_size).getT() / 2)
       
       
        #+ self.matrices['center'] - (matrix(hat.size) /2)
        return tuple(map(int, top.getA1()))


    def decorate(self, im):
        """Decorate an image with face data."""

        color = (232, 118, 0)
        red = (0xD0, 0x20, 0x00)#D20


        box = self.matrices['rotation'].dot(self.matrices['bbox']).getT() + self.matrices['center']
        draw = ImageDraw.Draw(im)
        draw.polygon(map(int, box.getA1()))

        top = self.matrices['rotation'] * matrix([
            [0], [-self.face['height']]
        ]) + self.matrices['center'].getT()

        bottom = self.matrices['rotation'] * matrix([
            [0], [self.face['height']]
        ]) + self.matrices['center'].getT()

        center_x, center_y  = self.face['center']
        draw.line([(center_x, center_y), (center_x, center_y - self.face['height'])],
                  fill=color)
        draw.line([tuple(top.getA1()), tuple(bottom.getA1())], fill=red)

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
        new_hat = new_hat.resize(resize_to)

        coords = self.find_coords(resize_to)
        print "coords: ", coords

        face.paste(new_hat, coords, new_hat)
        self.decorate(im)
        return face


def scumbagify(face, url):
    """Place the hat on the image at `url` and upload to s3.

    returns uploaded public URL."""
    tag = face.faces_detect(url)
    if tag['status'] != 'success':
        raise Exception("Retrieving tags not successful. %s" % tag['status'])


if __name__ == '__main__':
    with open(os.path.join('..', 'daniel.json')) as f:
        resp = json.load(f)

    url = resp['photos'][0]['url']
    with closing(urllib.urlopen(url)) as f:
        facef = tempfile.TemporaryFile()
        facef.write(f.read())
    facef.seek(0)
    face = Image.open(facef)
    f = Face(resp)
    f.scumbagify(face)
    face.save('../test.png')
