import time
import glob
import jsonschema
import os
from os.path import join
import main as scraper, validate, utils
import shutil
from conf import PROJECT_DIR, XML_REV, XML_DIR
from flask import Flask, request, render_template, redirect, flash, send_from_directory

#from conf import logging


app = Flask(__name__, **{
    'template_folder': join(PROJECT_DIR, 'web', 'templates'),
    'static_folder': join(PROJECT_DIR, 'web', 'static'),
})

def render(template, *args, **kwargs):
    # template_path should always be relative to project root.
    # always use absolute paths.
    kwargs.update({'args': args})
    return render_template(template, **kwargs)

def listfiles(path, ext_list=None):
    "returns a list of absolute paths for given dir"
    path_list = map(lambda fname: os.path.abspath(join(path, fname)), os.listdir(path))
    if ext_list:
        path_list = filter(lambda path: os.path.splitext(path)[1] in ext_list, path_list)
    return sorted(filter(os.path.isfile, path_list))

def uploads():
    return listfiles(upload_path(), ext_list=['.xml', '.json'])


def upload_path(fname=None, check_exists=True):
    path = app.config['UPLOAD_FOLDER']
    if fname:
        path = join(path, fname)
        if check_exists and not os.path.exists(path):
            return None
    return path

def timed(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        # print '%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0)
        # return ret
        return (time2 - time1, ret)
    return wrap

#
#
#

@app.route("/upload/", methods=['POST'])
def upload():
    "upload jats xml, generate xml, validate"
    if not 'xml' in request.files:
        flash('xml file not found')
        return redirect("/")

    # upload
    xml = request.files['xml']
    filename = xml.filename # todo: sanitize this
    if not os.path.splitext(filename)[1] == '.xml':
        flash("only xml uploads, please")
        return redirect("/")
    path = join(app.config['UPLOAD_FOLDER'], filename)
    xml.save(path)

    # generate
    try:
        # print 'generating'
        results = scraper.main(path)
        json_filename = filename + '.json'
        json_path = join(app.config['UPLOAD_FOLDER'], json_filename)
        open(json_path, 'w').write(results)
        flash("generated %s" % json_filename)
    except Exception as err:
        flash(err)
        return redirect("/")

    # validate
    try:
        # print 'validating'
        validate.main(open(json_path, 'r'))
        flash("valid")
    except jsonschema.ValidationError as err:
        flash("invalid: " + str(err))

    return redirect("/")


@app.route('/search/', methods=['POST'])
def search():
    if not 'msid' in request.form:
        flash("nada")
        return redirect('/')
    try:
        msid = utils.pad_msid(request.form['msid'])
    except Exception as err:
        flash("unhandled error attempting to wrangle a manuscript ID: %s" % str(err))
        return redirect('/')

    xml_files = glob.glob(XML_DIR + '/elife-%s-v*.xml' % msid)

    if len(xml_files) > 6:
        flash("given msid matches too many files. please be more specific")
        return redirect('/')

    def copy_file_to_uploads(path):
        fname = os.path.basename(path)
        new_path = upload_path(fname, check_exists=False)
        if os.path.exists(new_path):
            os.unlink(new_path)
        shutil.copy(path, new_path)
        flash("added %s" % fname)
        return new_path

    map(copy_file_to_uploads, xml_files)
    return redirect('/')


@app.route('/upload/<filename>')
def uploaded_file(filename):
    "serve uploaded files"
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    "delete a file from the uploads dir"
    path = upload_path(filename)
    if not path:
        flash("file not found")
    else:
        os.unlink(path)
        return redirect("/")

@app.route('/validate/<filename>', methods=['POST'])
def validate_file(filename):
    "validates generated article-json"
    path = upload_path(filename)
    if not path:
        flash("file not found")
    elif not filename.endswith('.json'):
        flash("not validated: I can only validate .json files")
    else:
        try:
            t, _ = timed(validate.main)(open(path, 'r'))
            flash("valid (%s seconds)" % round(t, 3))
        except jsonschema.ValidationError as err:
            flash("invalid: " + str(err))
    return redirect("/")

@app.route('/generate/<filename>', methods=['POST'])
def generate_file(filename):
    "generates the article-json for an uploaded file"
    path = upload_path(filename)
    if not path:
        flash("file not found")
    elif not filename.endswith('.xml'):
        flash("can only generate .xml files")
    else:
        try:
            t, results = timed(scraper.main)(path)
            open(path + '.json', 'w').write(results)
            flash("regenerated %s (%s seconds)" % (filename, round(t, 3)))
        except Exception as err:
            flash(err)
    return redirect("/")

@app.route("/")
def index():
    context = {
        'xml_rev': XML_REV,
        'uploaded_files': map(lambda path: (path, os.path.basename(path)), sorted(uploads())),
    }
    return render('index.html', **context)

def start_server():
    app.config.update({
        'DEBUG': False,
        'SECRET_KEY': os.urandom(24),
        # http://flask.pocoo.org/docs/0.11/config/#instance-folders
        'UPLOAD_FOLDER': join(PROJECT_DIR, 'web', 'uploads'),
    })
    app.run()

if __name__ == '__main__':
    start_server()
