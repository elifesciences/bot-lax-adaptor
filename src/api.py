import os
from os.path import join
import conf
from flex.core import validate
import flex
import connexion
from flask import request
import main as scraper, validate as ajson_validate
import jsonschema
from connexion.resolver import RestyResolver

#
#
#

def validates(spec):
    path = join(conf.PROJECT_DIR, 'schema', 'api.yaml')
    spec = flex.load(path)
    validate(spec)
    return True


#
#
#

class AsdfResolver(RestyResolver):
    """custom resolver that flattens func name lookup after initial module.
    RestyResolver parent assumes icky classes with .post and .search methods"""

    def resolve_operation_id_using_rest_semantics(self, operation):
        # ll: api.xml.search
        orig_path = super(AsdfResolver, self).resolve_operation_id_using_rest_semantics(operation)
        bits = orig_path.split('.') # ll ['api', 'xml', 'search']

        module = bits[0] # ll: 'api'
        # the funname resolution is wonky, so discard it
        method = bits[-1] # ll: 'search'

        path = operation.path # ll: /ajson/validation/{filename}
        # we want something like:
        # /ajson/validation/{filename} => ajson_validation
        # /ajson/{filename}/validation => ajson_validation
        bits = path.strip('/').split('/') # => ['ajson', 'validation', '{filename}']
        bits = filter(lambda bit: bit and not bit.startswith('{') and not bit.endswith('}'), bits)
        fnname = '_'.join(bits) # ll: ajson_validation
        return '%s.%s_%s' % (module, method, fnname) # ll: api.post_ajson_validation


def listfiles(path, ext_list=None):
    "returns a list of absolute paths for given dir"
    path_list = map(lambda fname: os.path.abspath(join(path, fname)), os.listdir(path))
    if ext_list:
        path_list = filter(lambda path: os.path.splitext(path)[1] in ext_list, path_list)
    return sorted(filter(os.path.isfile, path_list))


#
# api
#

UPLOAD_FOLDER = join(conf.PROJECT_DIR, 'web', 'uploads')
NOT_IMPLEMENTED = {}, 501

def search_xml():
    paths = listfiles(UPLOAD_FOLDER, ext_list=['.xml'])
    return map(os.path.basename, paths)

def post_xml():
    "upload jats xml, generate xml, validate"
    if not 'xml' in request.files:
        #flash('xml file not found')
        # return redirect("/")
        return {'error': 'not found'}

    # upload
    xml = request.files['xml']
    filename = xml.filename # todo: sanitize this
    if not os.path.splitext(filename)[1] == '.xml':
        #flash("only xml uploads, please")
        # return redirect("/")
        return {'error': "file doesn't look like xml"}
    path = join(UPLOAD_FOLDER, filename)
    xml.save(path)

    # generate
    try:
        # print 'generating'
        results = scraper.main(path)
        json_filename = filename + '.json'
        json_path = join(UPLOAD_FOLDER, json_filename)
        open(json_path, 'w').write(results)
        #flash("generated %s" % json_filename)
    except Exception as err:
        # flash(err)
        # return redirect("/")
        return {'error': str(err)}

    # validate
    try:
        # print 'validating'
        ajson_validate.main(open(json_path, 'r'))
        # flash("valid")
        return {'error': 'success'}
    except jsonschema.ValidationError as err:
        #flash("invalid: " + str(err))
        return {'error': 'invalid'}

    # return redirect("/")

def search_ajson():
    paths = listfiles(UPLOAD_FOLDER, ext_list=['.json'])
    return map(os.path.basename, paths)

def post_ajson_validate():
    return NOT_IMPLEMENTED

def post_ajson_generate(filename):
    return NOT_IMPLEMENTED

def main():
    APP = connexion.App(__name__, specification_dir=join(conf.PROJECT_DIR, 'schema'))
    APP.add_api('api.yaml', resolver=AsdfResolver('api'))
    APP.app.config.update({
        #'DEBUG': True,
        'SECRET_KEY': os.urandom(24),
        # http://flask.pocoo.org/docs/0.11/config/#instance-folders
        'UPLOAD_FOLDER': UPLOAD_FOLDER,
        # Flask/Jinja caches templates
        'TEMPLATES_AUTO_RELOAD': True
    })
    APP.run(port=8080)  # , #debug=True)

if __name__ == '__main__':
    main()
