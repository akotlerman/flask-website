from flask import Blueprint, render_template, flash, request, redirect, url_for, jsonify, abort
from app.extensions import cache, pages
from app.tasks import long_task

main = Blueprint('main', __name__)


@main.route('/')
@cache.cached(timeout=1000)
def home():
    return render_template('index.html')


@main.route('/task', methods=['GET', 'POST'])
def index():
    return render_template("longtask.html")


@main.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.apply_async()
    return jsonify({}), 202, {'Location': url_for('main.taskstatus',
                                                  task_id=task.id)}


@main.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background jobself.get
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@main.route('/<path:folder>/<path:path>/')
def page(folder, path):
    return render_template('page.html', folder=folder, page=pages.get_or_404(folder, path), page_title=path)


@main.route('/<path:folder>/')
def folder(folder):
    folder_dict = sorted(pages.get_or_404(folder=folder))
    page_title = folder.replace('_', ' ').title()
    return render_template('folder.html', folder=folder, pages=folder_dict, page_title=page_title)


@main.route('/topics/')
def folders():
    return render_template('folders.html', folders=pages._pages)
