from StringIO import StringIO
import traceback
import os, json, uuid
from os.path import join
import conf, utils, adaptor
from flex.core import validate
import flex
import connexion
import flask
from flask import request
import main as scraper, validate as ajson_validate
import jsonschema
from connexion.resolver import RestyResolver
from werkzeug.exceptions import HTTPException
import logging

LOG = logging.getLogger(__name__)

# just the default, can be overriden when creating an app
UPLOAD_FOLDER = join(conf.PROJECT_DIR, 'web', 'uploads')

#
# utils
#

def validate_schema():
    "validates the api scheme"
    path = join(conf.PROJECT_DIR, 'schema', 'api.yaml')
    spec = flex.load(path)
    validate(spec)
    return True

def http_exception(code, msg):
    "returns an HTTPException object with the correct code and message set"
    ex = HTTPException(msg)
    ex.code = code
    return ex

def http_ensure(case, msg, code=400):
    "if not case, raise a client error exception (by default)"
    if not case:
        raise http_exception(code, msg)

def listfiles(path, ext_list=None):
    "returns a pair of (basename_list, absolute_path_list) for given dir, optionally filtered by extension"
    path_list = map(lambda fname: os.path.abspath(join(path, fname)), os.listdir(path))
    if ext_list:
        path_list = filter(lambda path: os.path.splitext(path)[1] in ext_list, path_list)
    path_list = sorted(filter(os.path.isfile, path_list))
    return map(os.path.basename, path_list), path_list

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
        # the funname resolution is wonky, so discard it
        method = bits[-1] # ll: 'search'

        path = operation.path # ll: /article-json/validation/{filename}
        # we want something like:
        # /article-json/validation/{filename} => article_json_validation
        # /article-json/{filename}/validation => article_json_validation
        bits = path.strip('/').split('/') # => ['article-json', 'validation', '{filename}']
        bits = filter(lambda bit: bit and not bit.startswith('{') and not bit.endswith('}'), bits)
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
    return xml_files()[0] # just the basenames

def search_article_json():
    return article_json_files()[0] # just the basenames

def get_article_json(filename):
    basenames, full_paths = article_json_files()
    if not filename:
        return basenames
    http_ensure(filename in basenames, "requested file not found", 404)
    idx = dict(zip(basenames, full_paths))
    return json.load(open(idx[filename], 'r'))

def post_xml():
    "upload jats xml, generate xml, validate, send to lax as a dry run"
    http_ensure('xml' in request.files, "xml file required", 404)

    # upload
    try:
        xml = request.files['xml']
        filename = xml.filename # todo: sanitize this. assumes a name like 'elife-00000-v1.xml'
        http_ensure(os.path.splitext(filename)[1] == '.xml', "file doesn't look like xml")
        path = join(upload_folder(), filename)
        xml.save(path)
    except Exception as err:
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': 'error',
            'code': 'error-uploading-xml',
            'message': 'an error occured uploading the article xml to be processed',
            'trace': sio.getvalue(),
        }, 400 # everything is always the client's fault.

    # generate
    try:
        override = scraper.deserialize_overrides(request.form.getlist('override'))
        article_json = scraper.main(path, {'override': override})
        json_filename = filename + '.json'
        json_path = join(upload_folder(), json_filename)
        open(json_path, 'w').write(article_json)
    except Exception as err:
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': 'error',
            'code': 'error-scraping-xml',
            'message': str(err),
            'trace': sio.getvalue()
        }, 400

    # validate
    try:
        ajson_validate.main(open(json_path, 'r'))

    except jsonschema.ValidationError as err:
        return {
            'status': 'invalid',
            'code': 'invalid-article-json',
            'message': 'the generated article-json failed validation',
            'trace': str(err), # todo: any good?
        }, 400
    except Exception as err:
        sio = StringIO()
        traceback.print_exc(file=sio)
        return {
            'status': 'error',
            'code': 'error-validating-article-json',
            'message': 'an error occurred attempting to validate the generated article-json',
            'trace': sio.getvalue()
        }, 400

    # send to lax
    try:
        msid, version = utils.version_from_path(filename)
        token = uuid.uuid4()
        args = {
            # the *most* important parameter. don't modify lax.
            'dry_run': True,

            # a forced ingest by default
            'action': 'ingest',
            'force': True,

            # article details
            'id': msid,
            'version': int(version),
            'article_json': article_json,

            'token': token,
        }
        lax_resp = adaptor.call_lax(**args)
        LOG.info("lax response", extra=lax_resp)

        #api_resp = copy.deepcopy(lax_resp)
        api_resp = utils.subdict(lax_resp, ['status', 'code', 'message', 'trace'])

        if api_resp['status'] in [adaptor.INVALID, adaptor.ERROR]:
            # failure
            return api_resp, 400

        # success
        # 'code', 'message' and 'trace' are not returned by lax on success, just 'status'
        api_resp['ajson'] = json.loads(article_json)['article']
        api_resp['override'] = override
        return api_resp, 200

    except Exception as err:
        # lax returned something indecipherable
        return {
            'status': 'error',
            'code': 'lax-is-borked',
            'message': "lax responded with something that couldn't be decoded",
            'trace': str(err),
        }, 400

def create_app(cfg_overrides=None):
    app = connexion.App(__name__, specification_dir=join(conf.PROJECT_DIR, 'schema'))
    app.add_api('api.yaml', resolver=BotLaxResolver('api'))
    cfg = {
        'SECRET_KEY': os.urandom(24), # necessary for uploads
        # http://flask.pocoo.org/docs/0.11/config/#instance-folders
        'UPLOAD_FOLDER': UPLOAD_FOLDER,
    }
    if cfg_overrides:
        cfg.update(cfg_overrides)
    app.app.config.update(cfg)
    return app

def main():
    app = create_app({
        #'DEBUG': True,
        # Flask/Jinja caches templates
        'TEMPLATES_AUTO_RELOAD': True
    })
    app.run(port=8080)

if __name__ == '__main__':
    main()
