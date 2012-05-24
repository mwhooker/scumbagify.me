from flask import Flask, abort, jsonify, json, make_response, request
#from flaskext.cache import Cache
from werkzeug.contrib.fixers import ProxyFix

from . import scumbagify, config


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_object(config)

#cache = Cache(app)

from face_client import face_client

face = face_client.FaceClient(
    app.config.get('API_KEY'),
    app.config.get('API_SECRET')
)


@app.route('/')
def index():
    url = app.request.data.get('url')
    face_img = scumbagify(face, url)

    abort(500)
