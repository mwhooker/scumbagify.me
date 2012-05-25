import tempfile
import mimetypes
import urllib
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from contextlib import closing
from face_client import face_client
from hashlib import md5
from PIL import Image
from flask import Flask, render_template, request
from werkzeug.contrib.fixers import ProxyFix

from . import scumbagify, config, __version__


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_object(config)

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
    url = request.args.get('src')
    debug = request.args.get('debug')
    if not url:
        return render_template('index.html')
    mtype, encoding = mimetypes.guess_type(url)

    key = Key(bucket)
    key.key = "%s%s_%s" % (
        __version__,
        'D' if app.config['DEBUG'] or debug else '',
        md5(url).hexdigest()
    )

    if not key.exists():
        resp = face.faces_detect(urls=url)

        if resp['status'] != 'success':
            raise Exception("Retrieving tags not successful. %s" % resp['status'])

        # download img to tempfile and construct PIL obj
        imgf = tempfile.TemporaryFile()
        with closing(urllib.urlopen(url)) as f:
            imgf.write(f.read())
        imgf.seek(0)
        img = Image.open(imgf)

        # Show original picture if we can't find any scumbags
        try:
            scumbagify.scumbagify(img, resp, app.config.get('DEBUG') or debug)
        except scumbagify.FaceNotFound:
            return render_template('redirect.html', url=url)

        outf = tempfile.TemporaryFile()
        img.save(outf, img.format)

        key.set_metadata('original', url)
        key.set_metadata('Content-Type', mtype)
        key.set_contents_from_file(outf, reduced_redundancy=True, rewind=True)
        key.make_public()

    return render_template(
        'redirect.html',
        url='https://s3.amazonaws.com/scumbagifyme/%s' % key.name
    )
