import json
import logging
import os
from os.path import join
from io import StringIO
import traceback
import uuid
import connexion
from connexion.resolver import RestyResolver
import flask
from flask import request
import flex
from flex.core import validate
import jsonschema
from werkzeug.exceptions import HTTPException
import adaptor, conf, utils, main as scraper, validate as ajson_validate
from utils import lmap, lfilter, first

LOG = logging.getLogger(__name__)

#
# utils
#

def validate_schema():
    "validates the api schema"
    path = join(conf.PROJECT_DIR, 'schema', 'api.yaml')
    spec = flex.load(path)
    validate(spec)
    return True

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

class BotLaxResolver(RestyResolver):
    """custom resolver that flattens func name lookup after initial module.
    RestyResolver parent assumes icky classes with .post and .search methods"""

    def resolve_operation_id_using_rest_semantics(self, operation):
        # ll: api.xml.search
        orig_path = super(BotLaxResolver, self).resolve_operation_id_using_rest_semantics(operation)
        bits = orig_path.split('.') # ll ['api', 'xml', 'search']

        module = bits[0] # ll: 'api'
        # the funcname resolution is wonky, so discard it
        method = bits[-1] # ll: 'search'

        path = operation.path # ll: /article-json/validation/{filename}
        # we want something like:
        # /article-json/validation/{filename} => article_json_validation
        # /article-json/{filename}/validation => article_json_validation
        bits = path.strip('/').split('/') # => ['article-json', 'validation', '{filename}']
        bits = lfilter(lambda bit: bit and not bit.startswith('{') and not bit.endswith('}'), bits)
        fnname = '_'.join(bits).replace('-', '_') # ll: article_json_validation
        return '%s.%s_%s' % (module, method, fnname) # ll: api.post_article_json_validation

def article_json_files():
    return listfiles(upload_folder(), ext_list=['.json'])

def xml_files():
    return listfiles(upload_folder(), ext_list=['.xml'])

#
# api
#

def search_xml():
    "GET /xml"
    return first(xml_files()) or [] # just the basenames

def search_article_json():
    return first(article_json_files()) or [] # just the basenames

def get_article_json(filename):
    basenames, full_paths = article_json_files()
    if not filename:
        return basenames
    http_ensure(filename in basenames, "requested file not found", 404)
    idx = dict(zip(basenames, full_paths))
    return json.load(open(idx[filename], 'r'))

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
        } # shouldn't this be a 400?

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
        }, 400 # shouldn't this be a 500?

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
        #msid, version = utils.version_from_path(filename)
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
    app = connexion.App(__name__, specification_dir=join(conf.PROJECT_DIR, 'schema'))
    app.add_api('api.yaml', resolver=BotLaxResolver('api'), strict_validation=True)
    cfg = {
        'SECRET_KEY': os.urandom(24), # necessary for uploads
        # http://flask.pocoo.org/docs/0.11/config/#instance-folders
        'UPLOAD_FOLDER': conf.API_UPLOAD_FOLDER,
    }
    if cfg_overrides:
        cfg.update(cfg_overrides)
    app.app.config.update(cfg)
    return app

def main():
    app = create_app({
        # 'DEBUG': True,
        # Flask/Jinja caches templates
        'TEMPLATES_AUTO_RELOAD': True
    })
    app.run(port=8080)

if __name__ == '__main__':
    main()
