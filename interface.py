#!/usr/bin/python3

from flask import Flask, render_template, request, redirect
import variables as var
import util
import os.path
from os import listdir
import random
from werkzeug.utils import secure_filename

class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        real_ip = environ.get('HTTP_X_REAL_IP', '')
        if real_ip:
            environ['REMOTE_ADDR'] = real_ip
        return self.app(environ, start_response)


web = Flask(__name__)


def init_proxy():
    global web
    if var.is_proxified:
        web.wsgi_app = ReverseProxied(web.wsgi_app)


@web.route("/", methods=['GET', 'POST'])
def index():
    folder_path = var.music_folder
    files = util.get_recursive_filelist_sorted(var.music_folder)
    music_library = util.Dir(folder_path)
    for file in files:
        music_library.add_file(file)

    if request.method == 'POST':
        print(request.form)
        if 'add_file' in request.form and ".." not in request.form['add_file']:
            item = ('file', request.form['add_file'])
            var.playlist.append(item)
        if ('add_folder' in request.form and ".." not in request.form['add_folder']) or ('add_folder_recursively' in request.form and ".." not in request.form['add_folder_recursively']) :
            try:
                folder = request.form['add_folder']
            except:
                folder = request.form['add_folder_recursively']

            if not folder.endswith('/'):
                folder += '/'

            print('folder:', folder)
            if 'add_folder_recursively' in request.form:
                files = music_library.get_files_recursively(folder)
            else:
                files = music_library.get_files(folder)
            files = list(map(lambda file: ('file', folder + '/' + file), files))
            print('Adding to playlist: ', files)
            var.playlist.extend(files)
        elif 'delete_music' in request.form:
            try:
                var.playlist.remove("file", request.form['delete_music'])
            except ValueError:
                pass
        elif 'action' in request.form:
            action = request.form['action']
            if action == "randomize":
                random.shuffle(var.playlist)
    if var.current_music:
        current_music = var.current_music[len(var.music_folder):]
    else:
        current_music = None

    return render_template('index.html',
                           current_music=current_music,
                           user=var.user,
                           playlist=var.playlist,
                           all_files=files,
                           music_library=music_library)


@web.route('/download', methods=["POST"])
def download():
    print(request.form)

    file = request.files['music_file']
    if not file:
        return redirect("./", code=406)
    elif file.filename == '':
        return redirect("./", code=406)
    elif '..' in request.form['directory']:
        return redirect("./", code=406)

    if file.name == "music_file" and "audio" in file.headers.to_list()[1][1]:
        web.config['UPLOAD_FOLDER'] = var.music_folder + request.form['directory']
        filename = secure_filename(file.filename)
        print(filename)
        file.save(os.path.join(web.config['UPLOAD_FOLDER'], filename))
        return redirect("./", code=302)
    else:
        return redirect("./", code=409)


if __name__ == '__main__':
    web.run(port=8181, host="127.0.0.1")
