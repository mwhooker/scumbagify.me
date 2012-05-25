__version__ = "0.1"

import tempfile
import mimetypes
import urllib
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from contextlib import closing
from face_client import face_client
from hashlib import md5
from PIL import Image
from flask import Flask, abort, redirect, request
#from flaskext.cache import Cache
from werkzeug.contrib.fixers import ProxyFix

from . import scumbagify, config


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_object(config)

#cache = Cache(app)


s3 = S3Connection(
    app.config.get('AWS_KEY'),
    app.config.get('AWS_SECRET')
)
bucket = s3.get_bucket('scumbagifyme')

face = face_client.FaceClient(
    app.config.get('FACE_KEY'),
    app.config.get('FACE_SECRET')
)


@app.route('/')
def index():
    url = request.args.get('url')
    mtype, encoding = mimetypes.guess_type(url)
    ext = (set(mimetypes.guess_all_extensions(mtype)) - set(['.jpe'])).pop()

    key = Key(bucket)
    key.key = "%s_%s%s" % (
        __version__,
        md5(url).hexdigest(),
        ext
    )


    if not key.exists():
        resp = face.faces_detect(urls=url)

        with closing(urllib.urlopen(url)) as f:
            imgf = tempfile.TemporaryFile()
            imgf.write(f.read())
        imgf.seek(0)
        img = Image.open(imgf)

        try:
            scumbagify.scumbagify(img, resp)
        except scumbagify.FaceNotFound:
            return redirect(url)

        outf = tempfile.TemporaryFile()
        img.save(outf, img.format)

        key.set_metadata('original', url)
        key.set_metadata('Content-Type', mtype)
        key.set_contents_from_file(outf, reduced_redundancy=True, rewind=True)
        key.make_public()

    return redirect(
        'https://s3.amazonaws.com/scumbagifyme/%s' % key.name
        #key.generate_url(7 * 24 * 60 * 60)
    )


def scumbagify_url(face, url):
    """Place the hat on the image at `url` and upload to s3.

    returns uploaded public URL."""
    tag = face.faces_detect(url)
    if tag['status'] != 'success':
        raise Exception("Retrieving tags not successful. %s" % tag['status'])

