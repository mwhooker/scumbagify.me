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


        """
        #self.matrices['rotated'] = self.matrices['rotation'] * self.matrices['bbox']

        for c in self.matrices['bboxA']:
            print c

        self.matrices['rotated'] = [
            self.matrices['rotation'] * c for c in self.matrices['bboxA']
        ]
        print [r * self.matrices['center'] for r in self.matrices['rotated']]
        #print self.matrices['bbox'] + self.matrices['center']
        
        ulm = self.rotation_matrix * matrix([
            [-self.face['width']],
            [-self.face['height']]
        ])
        lrm = self.rotation_matrix * matrix([
            [self.face['width']],
            [self.face['height']]
        ])
        self.face['upper_left'] = (
            ulm[0][0] + self.face['center'][0],
            ulm[1][0] + self.face['center'][1]
        )
        self.face['lower_right'] = (
            lrm[0][0] + self.face['center'][0],
            lrm[1][0] + self.face['center'][1]
        )
        """


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

        width = self.face['width'] * 1.8

        print "hat size, ", hat.size
        print "width: ", width
        print "scale factor: ", width / hat.size[0]
        return map(int, (width, hat.size[1] * (width / hat.size[0])))


    def find_coords(self, hat_size):
        """Find where we should place the hat."""

        """
            roll = math.radians(tag['roll'])
            roll_x = math.sin(roll) * face_height
            return tuple(map(int, (
# relative to hat size
                center_x - hat_size[0] / 2,
                (center_x + roll_x),# - hat_size[0] / 2,
        """

        center_x, center_y  = self.face['center']
        return tuple(map(int, (
            0, 0
            # relative to hat size
           # self.face['upper_left'][0] - HAT_LEFT_MARGIN,
            #center_x - hat_size[0] / 2,
            # top of hat relative to face
           # self.face['upper_left'][1] - HAT_TOP_MARGIN
            #center_y - (self.face['height'] * 1.35)
        )))


    def decorate(self, im):
        """Decorate an image with face data."""

        color = (232, 118, 0)
        red = (0xD0, 0x20, 0x00)#D20

        for t in [i for i in self.tag if isinstance(self.tag[i], dict)]:
            if 'x' in self.tag[t]:
                x = self.norm_x(self.tag[t]['x'])
                y = self.norm_y(self.tag[t]['y'])
                print "%s: (%s, %s)" % (t, x, y)
                im.putpixel((x, y), color)
                im.putpixel((x, y+1), color)
                im.putpixel((x+1, y), color)
                im.putpixel((x+1, y+1), color)


        box = self.matrices['rotation'].dot(self.matrices['bbox']).getT() + self.matrices['center']
        print map(int, box.getA1())
        draw = ImageDraw.Draw(im)
        draw.polygon(map(int, box.getA1()))


        """
        im.putpixel(self.face['upper_left'], color)
        center_x, center_y  = self.face['center']
        top = self.rotation_matrix * matrix([
            [0], [-self.face['height']]
        ])
        bottom = self.rotation_matrix * matrix([
            [0], [self.face['height']]
        ])
        top = (top[0][0] + center_x, top[1][0] + center_y)
        bottom = (bottom[0][0] + center_x, bottom[1][0] + center_y)

        draw.line([(center_x, center_y), (center_x, center_y - self.face['height'])],
                  fill=color)
        draw.line([top, bottom], fill=red)
        draw.polygon((
            self.face['upper_left'],
            self.face['upper_right'],
            self.face['lower_left'],
            self.face['lower_right']
        ))
        """


    def scumbagify(self, im):
        self.decorate(im)

        rotation = self.find_rotation()
        print "rotation: ", rotation
        new_hat = hat.rotate(rotation)

        resize_to = self.find_scale()
        print "resize to: ", resize_to
        new_hat = new_hat.resize(resize_to)

        coords = self.find_coords(resize_to)
        print "coords: ", coords

        face.paste(new_hat, coords, new_hat)
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
