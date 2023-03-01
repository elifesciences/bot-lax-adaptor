import json
import logging
import os
from os.path import join
from io import StringIO
import traceback
import uuid
import flask
from flask import request
import jsonschema
from werkzeug.exceptions import HTTPException
import adaptor, conf, utils, main as scraper, validate as ajson_validate
from utils import lmap, lfilter, first
from flask import Blueprint

LOG = logging.getLogger(__name__)

urls = Blueprint('urls', __name__,)

#
# utils
#

def http_ensure(case, msg, code=400):
    "if not case, raise a client error exception (by default)"
    if not case:
        ex = HTTPException(msg)
        ex.code = code
        raise ex

def listfiles(path, ext_list=None):
    "returns a pair of (basename_list, absolute_path_list) for given dir, optionally filtered by extension"
    path_list = lmap(lambda fname: os.path.abspath(join(path, fname)), os.listdir(path))
    if ext_list:
        path_list = lfilter(lambda path: os.path.splitext(path)[1] in ext_list, path_list)
    path_list = sorted(filter(os.path.isfile, path_list))
    return lmap(os.path.basename, path_list)

#
#
#

def upload_folder():
    return flask.current_app.config['UPLOAD_FOLDER']

def article_json_files():
    return listfiles(upload_folder(), ext_list=['.json'])

def xml_files():
    return listfiles(upload_folder(), ext_list=['.xml'])

#
# api
#

@urls.route("/xml", methods=["GET"])
def search_xml():
    "GET /xml"
    return first(xml_files()) or [] # just the basenames

@urls.route("/article-json", methods=["GET"])
def search_article_json():
    return first(article_json_files()) or [] # just the basenames

@urls.route("/article-json/<string:filename>", methods=["GET"])
def get_article_json(filename):
    basenames, full_paths = article_json_files()
    if not filename:
        return basenames
    http_ensure(filename in basenames, "requested file not found", 404)
    idx = dict(zip(basenames, full_paths))
    return json.load(open(idx[filename], 'r'))

@urls.route("/xml", methods=["POST"])
def post_xml():
    "upload jats xml, generate xml, validate, send to lax as a dry run"
    http_ensure('xml' in request.files, "xml file required", 400)

    try:
        override = scraper.deserialize_overrides(request.form.getlist('override'))
    except ValueError:
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': conf.ERROR,
            'code': conf.BAD_OVERRIDES,
            'message': 'an error occurred attempting to parse your given overrides.',
            'trace': sio.getvalue()
        }, 400

    # upload
    try:
        xml = request.files['xml']
        filename = os.path.basename(xml.filename)
        http_ensure(os.path.splitext(filename)[1] == '.xml', "file doesn't look like xml")
        path = join(upload_folder(), filename)
        xml.save(path)

    except Exception:
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': conf.ERROR,
            'code': conf.BAD_UPLOAD,
            'message': 'an error occured uploading the article xml to be processed',
            'trace': sio.getvalue(),
        }, 400 # shouldn't this be a 500? everything is always the client's fault.

    # generate
    try:
        article_json = scraper.main(path, {
            'override': override,
            'fill-missing-image-dimensions': True
        })
        json_filename = filename + '.json'
        json_path = join(upload_folder(), json_filename)
        open(json_path, 'w').write(article_json)

    except Exception as err:
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': conf.ERROR,
            'code': conf.BAD_SCRAPE,
            'message': str(err),
            'trace': sio.getvalue()
        }, 400

    # validate
    try:
        conf.API_PRE_VALIDATE and ajson_validate.main(open(json_path, 'r'))

    except jsonschema.ValidationError as err:
        return {
            'status': conf.INVALID,
            'code': conf.ERROR_INVALID,
            'message': 'the generated article-json failed validation, see trace for details.',
            'trace': str(err), # todo: any good?
        }, 400

    except Exception:
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': conf.ERROR,
            'code': conf.ERROR_VALIDATING,
            'message': 'an error occurred attempting to validate the generated article-json',
            'trace': sio.getvalue()
        }, 400 # TODO: shouldn't this be a 500?

    # send to lax
    try:
        # msid, version = utils.version_from_path(filename)
        msid = request.args['id']
        version = request.args['version']
        token = str(uuid.uuid4())
        args = {
            # the *most* important parameter. don't modify lax.
            'dry_run': True,

            # a forced ingest by default
            'action': conf.INGEST,
            'force': True,

            # article details
            'msid': msid,
            'version': int(version),
            'article_json': article_json,

            'token': token,
        }
        lax_resp = adaptor.call_lax(**args)

        context = utils.renkeys(lax_resp, [("message", "lax-message")])
        LOG.info("lax response", extra=context)

        api_resp = utils.subdict(lax_resp, ['status', 'code', 'message', 'trace'])

        if api_resp['status'] in [conf.INVALID, conf.ERROR]:
            # failure
            return api_resp, 400

        # success
        # 'code', 'message' and 'trace' are not returned by lax on success, just 'status'
        api_resp['ajson'] = json.loads(article_json)['article']
        api_resp['override'] = override
        return api_resp, 200

    except Exception:
        # lax returned something indecipherable
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': conf.ERROR,
            'code': conf.ERROR_COMMUNICATING,
            'message': "lax responded with something that couldn't be decoded",
            'trace': sio.getvalue(),
        }, 400 # TODO: shouldn't this be a 500?

def create_app(cfg_overrides=None):
    app = flask.Flask(__name__)
    cfg = {
        'SECRET_KEY': os.urandom(24), # necessary for uploads
        # http://flask.pocoo.org/docs/0.11/config/#instance-folders
        'UPLOAD_FOLDER': conf.API_UPLOAD_FOLDER,
    }
    if cfg_overrides:
        cfg.update(cfg_overrides)
    app.config.update(cfg)
    app.register_blueprint(urls)
    return app

# see `main()` for dev entry point and `wsgi.py` for non-dev entry point.
def main():
    app = create_app({
        # 'DEBUG': True,
        # Flask/Jinja caches templates
        'TEMPLATES_AUTO_RELOAD': True
    })
    app.run(port=8080)

if __name__ == '__main__':
    main()
