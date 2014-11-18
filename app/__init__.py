# -*- coding: utf-8 -*-

import os

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('config')

# Check and create UPLOAD_FULL_DIRECTORY recursively
# if it doesn't exist.
if not os.path.isdir(app.config["UPLOAD_FULL_DIRECTORY"]):
	try:
		os.makedirs(app.config["UPLOAD_FULL_DIRECTORY"])
	except:
		import traceback
		print traceback.format_exc()

db = SQLAlchemy(app)
db.create_all()

# Load filters and put into jinja_env.filters
import filter

map(lambda x: app.jinja_env.filters.update({x: filter.__dict__.get(x)}), filter.__all__)

import route
