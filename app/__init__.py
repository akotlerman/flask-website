#! ../env/bin/python

from flask import Flask, render_template
from webassets.loaders import PythonLoader as PythonAssetsLoader

from app import assets
from app.models import db
from app.controllers.main import main
from app import settings

from app.extensions import (
    cache,
    assets_env,
    debug_toolbar,
    login_manager,
    pages,
    celery
)

def create_app(object_name):
    """
    An flask application factory, as explained here:
    http://flask.pocoo.org/docs/patterns/appfactories/

    Arguments:
        object_name: the python path of the config object,
                     e.g. app.settings.ProdConfig
    """

    app = Flask(__name__)

    app.config.from_object(object_name)

    # initialize the cache
    cache.init_app(app)

    # initialize the debug tool bar
    debug_toolbar.init_app(app)

    # initialize SQLAlchemy
    db.init_app(app)

    # Initialize Celery
    celery.config_from_object(object_name)

    # Initialize Login Manager
    login_manager.init_app(app)

    # Initialize Flatpages
    pages.init_app(app)

    # Import and register the different asset bundles
    assets_env.init_app(app)
    assets_loader = PythonAssetsLoader(assets)
    for name, bundle in assets_loader.load_bundles().items():
        assets_env.register(name, bundle)

    # register error handlers
    def render_error(error):
        error_code = getattr(error, 'code', 500)
        return render_template('{0}.html'.format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)

    # register our blueprints
    app.register_blueprint(main)

    return app
