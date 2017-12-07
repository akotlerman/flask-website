from flask import Blueprint, render_template, flash, request, redirect, url_for, jsonify, abort
from app.extensions import cache, pages
from app.tasks import long_task
import flam3, io, base64, struct
from PIL import Image

main = Blueprint('main', __name__)


@main.route('/')
@cache.cached(timeout=1000)
def home():
    return render_template('index.html')


@main.route('/task', methods=['GET', 'POST'])
def index():
    return render_template("longtask.html")


@main.route('/adder')
def adder():
    return render_template("adder.html")


@main.route('/api/add_numbers')
def add_numbers():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b)


@main.route('/flam3')
def flam3_html():
    return render_template("flam3.html")


def hex_to_rgb(hexstr):
    return struct.unpack('BBB', b''.fromhex(hexstr[1:]))


@main.route('/api/gen_flam3')
def gen_flam3():
    point_count = request.args.get('point_count', 0, type=int)
    back_color = request.args.get('back_color', "#42426f", type=hex_to_rgb)
    front_color = request.args.get('front_color', "#f4a460", type=hex_to_rgb)
    selection_limiter = request.args.get('selection_limiter', None, type=str)
    colors = (back_color, front_color)

    print('selection is', selection_limiter)
    # Make sure selection limiter is sane
    if selection_limiter is None:
        selection_limiter = [False]*point_count
    else:
        selection_limiter = [bool(int(i)) for i in selection_limiter.split(',')]

    # Generate the fractal
    print(selection_limiter)
    mat_points = flam3.Fractal(point_count=point_count, selection_limiter=selection_limiter).execute()

    # Convert fractal data to a matrix of color
    img_mat = flam3.point_to_image_mat(mat_points)
    img = flam3.mat_to_color(img_mat, colors=colors)

    # Save data to BytesIO file object
    im = Image.fromarray(img)
    f = io.BytesIO()
    im.save(f, format='png')
    f.seek(0)
    return jsonify(result="data:image/png;base64,"+base64.b64encode(f.read()).decode())


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
