from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)
db.create_all()

import filter

map(lambda x: app.jinja_env.filters.update({x: filter.__dict__.get(x)}), filter.__all__)

import route
