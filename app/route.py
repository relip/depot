# -*- coding: utf-8 -*-

import os
import functools
import hashlib
import string
import random
import traceback
import json
import time
import mimetypes
import zipfile

from flask import render_template
from flask import send_from_directory
from flask import make_response
from flask import request
from flask import abort
from flask import session
from flask import url_for
from flask import redirect
from flask import send_file
from flask.ext.login import LoginManager
from flask.ext.login import login_required
from flask.ext.login import login_user
from flask.ext.login import logout_user
from flask.ext.login import current_user
from flask.ext.bcrypt import generate_password_hash, check_password_hash

import sqlalchemy
from sqlalchemy.exc import IntegrityError
from app import app
from app import db

import addon
import model
import file
import common

addon.init()

login_manager = LoginManager()
login_manager.init_app(app)

# Common functions

def _empty_string_to_none(s):
	return s if s != "" else None

@login_manager.user_loader
def load_user(uid):
	return model.User.query.filter(model.User.No == int(uid)).first()

@login_manager.unauthorized_handler
def unauthorized():
	return render_template("no_such_file.html")

# Decorators

def check_if_path_is_valid(mapper):
	def decorator(func):
		def wrapped_function(path, *args, **kwargs):
			fileQuery = mapper.query.filter(mapper.Path == path)
			fileData = fileQuery.first()

			if not fileData:
				return render_template("no_such_file.html")
			else:
				return func(path, fileData)

		return functools.update_wrapper(wrapped_function, func)
	return decorator

def check_if_file_is_valid():
	def decorator(func):
		def wrapped_function(no, *args, **kwargs):
			fileQuery = model.File.query.filter(model.File.No == no)
			fileData = fileQuery.first()

			if not fileData:
				return render_template("no_such_file.html")
			else:
				return func(no, fileData)
		return functools.update_wrapper(wrapped_function, func)
	return decorator

# View functions

@app.teardown_appcontext
def shutdown_session(exception=None):
	db.session.remove()

@app.route("/")
def index():
	if session.get("user_id", False):
		return redirect(url_for("overview"))
	return render_template("index.html")

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
	if request.method == 'POST' or request.form.get("test", None):
		optExpiresIn = _empty_string_to_none(request.form.get("expires_in", None))
		optDownloadLimit = _empty_string_to_none(request.form.get("download_limit", None))
		optHideAfterLimitExceeded = not not request.form.get("hide_after_limit_exceeded", False)
		optGroup = _empty_string_to_none(request.form.get("group"))

		if request.form.get("local", False) and request.form.get("path", False):
			if "\x00" in request.form["path"]:
				return json.dumps({"result": False})

			normalizedPath = os.path.abspath(request.form["path"]).lstrip("/")
			normalizedFullPath = os.path.join(app.config["UPLOAD_BASE_DIR"], normalizedPath)
			fd = file.store_local(normalizedPath)
			newPath = model.create_path(fd.No, os.path.basename(normalizedFullPath), "Web", optExpiresIn, optDownloadLimit,
				optHideAfterLimitExceeded, optGroup)
		else:
			fp = request.files["file"]
			fd = file.store(fp)
			newPath = model.create_path(fd.No, fp.filename, "Web", optExpiresIn, optDownloadLimit,
				optHideAfterLimitExceeded, optGroup)

		return json.dumps({"result": True, "path": newPath.Path})

	else:
		return render_template("upload.html")

@app.route("/api/regenerate_key")
@login_required
def api_regenerate_key():
	uinfo = load_user(session["user_id"])
	uinfo.APIKey = common.generate_random_string(32)
	db.session.commit()
	return redirect(url_for("overview"))

@app.route("/api/tweetbot", methods=["GET", "POST"])
def api_tweetbot():
	if not app.config.get("ENABLE_API", False):
		return abort(404)
	if not request.form["source"].startswith("Tweetbot for"):
		return abort(404)
	elif not model.User.query.filter(model.User.APIKey == request.args["api_key"]).first():
		return abort(403)
	else:
		print request.files
		fp = request.files["media"]
		fileName, fileExtension = os.path.splitext(fp.filename)
		fd = file.store(request.files["media"])
		newPath = model.create_path(fd.No, fp.filename, "Tweetbot")
		return json.dumps({"url": request.url_root + newPath.Path + fileExtension})

@app.route("/api/twitpic", methods=["GET", "POST"])
def api_twitpic():
	if not app.config.get("ENABLE_API", False):
		return abort(404)
	elif not model.User.query.filter(model.User.APIKey == request.args["api_key"]).first():
		return abort(403)
	else:
		print request.files
		fp = request.files["media"]
		fileName, fileExtension = os.path.splitext(fp.filename)
		fd = file.store(request.files["media"])
		newPath = model.create_path(fd.No, fp.filename, "Twitpic")
		return "<rsp status=\"ok\"><mediaurl>%s</mediaurl></rsp>" % (request.url_root + newPath.Path + fileExtension)

@app.route("/api/browse")
@login_required
def api_browse():
	if not app.config.get("ENABLE_REMOTE_BROWSER", False):
		return json.dumps({"result": False})
	if not request.args.get("path", False):
		return json.dumps({"result": False})
	if "\x00" in request.args["path"]:
		return json.dumps({"result": False})

	normalizedPath = os.path.abspath(request.args["path"]).lstrip("/")
	normalizedFullPath = os.path.join(app.config["UPLOAD_BASE_DIR"], normalizedPath)

	if not os.path.isdir(normalizedFullPath):
		return json.dumps({"result": False, "message": "Given path is not a directory"})

	buf = {
		"files": [],
		"directories": []
	}

	for fn in os.listdir(normalizedFullPath):
		absp = os.path.join(normalizedFullPath, fn)
		if os.path.isfile(absp):
			buf["files"].append({
				"name": fn,
				"size": os.stat(absp).st_size,
			})
		else:
			buf["directories"].append(fn)

	buf["files"].sort()
	buf["directories"].sort()

	return json.dumps({"result": True, "data": buf})


@app.route("/groups")
@login_required
def groups():
	return render_template("groups.html", groups=model.Group.query.all())

@app.route("/groups/create", methods=["GET", "POST"])
@login_required
def create_group():
	if request.method == "POST":
		if "group_path" in request.form:
			groupPath = request.form["group_path"]
			try:
				db.session.add(model.Group(groupPath,
					request.form.get("description", "")))
				db.session.commit()
			except IntegrityError:
				db.session.rollback()
				return json.dumps({"result": False, "error": "Already exists"})

		else:
			pathLength = 3 # default
			while True:
				try:
					groupPath = common.generate_random_string(int(pathLength))
					db.session.add(model.Group(groupPath,
						request.form.get("description", "")))
					db.session.commit()
					break
				except IntegrityError:
					db.session.rollback()
					pathLength += 0.2

		result = {}
		for p in request.form.get("paths", "").split(","):
			p = p.strip()
			if not p:
				continue
			fileData = model.Path.query.filter(model.Path.Path == p).first()

			if not fileData:
				result.update({p: False})

			fileData.Group = groupPath

			db.session.commit()

			result.update({p: True})

		db.session.commit()

		return json.dumps({"path": groupPath, "result": result})

	return render_template("groups_create.html")

@app.route("/group/<path>")
@check_if_path_is_valid(model.Group)
def group_information(path, groupData):
	return render_template("group.html", groupData=groupData, time=int(time.time()))

@app.route("/group/<path>/delete")
@login_required
@check_if_path_is_valid(model.Group)
def group_delete(path, groupData):
	try:
		groupQuery = model.Group.query.filter(model.Group.Path == path)
		groupQuery.delete()
		db.session.commit()
		return redirect(url_for("overview"))
	except:
		return traceback.format_exc()

@app.route("/group/<path>/modify", methods=["POST"])
@login_required
@check_if_path_is_valid(model.Group)
def group_modify(path, groupData):
	if "description" in request.form:
		groupData.Description = request.form["description"]
	db.session.commit()

	return json.dumps({"result": True})

@app.route("/group/<path>/zip")
@check_if_path_is_valid(model.Group)
def group_zip(path, groupData):
	if not app.config.get("ENABLE_API", True) and not app.config.get("ENABLE_ZIP", False):
		return abort(404)

	for fileData in groupData.Paths:
		if (fileData.DownloadLimit is not None and fileData.Downloaded >= fileData.DownloadLimit) or \
			(fileData.ExpiresIn is not None and time.time() > fileData.Uploaded + fileData.ExpiresIn):
			db.session.rollback()
			return render_template("limit_exceeded.html")
		else:
			fileData.Downloaded += 1
			db.session.commit()

	db.session.commit()

	zPath = os.path.join("/tmp", common.generate_random_string(32))
	zFp = zipfile.ZipFile(zPath, "w", app.config.get("ZIP_METHOD", zipfile.ZIP_DEFLATED))
	for fileData in groupData.Paths:
		zFp.write(os.path.join(app.config["UPLOAD_BASE_DIR"], fileData.File.StoredPath), fileData.ActualName)
	zFp.close()
	response = make_response(send_file(zPath))
	response.headers["Content-Disposition"] = "attachment; filename=\"%s.zip\""%(path)

	return response

@app.route("/signin", methods=["GET", "POST"])
def signin():
	if session.has_key("user_id"):
		return redirect(url_for("overview"))

	if "id" not in request.form or "password" not in request.form or request.method != "POST":
		return render_template("signin.html")

	userData = model.User.query.filter(model.User.ID == request.form["id"]).first()

	if not userData:
		return render_template("signin.html")
	elif not check_password_hash(userData.Password, request.form["password"]):
		return render_template("signin.html")
	else:
		login_user(userData)
		return(redirect(url_for("overview")))

@app.route("/signout")
@login_required
def signout():
	logout_user()
	return(redirect(url_for("signin")))

@app.route("/signup", methods=["GET", "POST"])
def signup():
	if not app.config.get("ENABLE_SIGNUP", False):
		return abort(404)

	elif (request.method == "POST" and
		request.form["id"] and request.form["password"]):
		u = model.User(request.form["id"], generate_password_hash(request.form["password"]), common.generate_random_string(32))
		db.session.add(u)
		db.session.commit()
		return redirect(url_for("signin"))
	else:
		return render_template("signup.html")

@app.route("/overview")
@login_required
def overview():
	uinfo = load_user(session["user_id"])
	paths = model.Path.query.order_by(model.Path.Uploaded.desc())

	try:
		page = int(request.args.get("page", 0))
		page = 0 if page <= 0 else page-1
		offset = page*50
	except:
		offset = 0

	pathList = paths.limit(50).offset(offset)
	pathCount = paths.count()
	pathSizeSum = db.session.query(sqlalchemy.func.sum(model.File.Size).label("sum")).join(model.Path.File).all()
	fileSizeSum = db.session.query(sqlalchemy.func.sum(model.File.Size).label("sum")).all()

	return render_template("overview.html", paths=pathList.all(), pathCount=pathCount,
		pathSizeSum=pathSizeSum, fileSizeSum=fileSizeSum, userInfo=uinfo)

# Path related

@app.route("/<path>")
@check_if_path_is_valid(model.Path)
def path_information(path, fileData):
	if not session.get("user_id") and \
			((fileData.DownloadLimit is not None and fileData.Downloaded >= fileData.DownloadLimit) or \
			(fileData.ExpiresIn is not None and time.time() > fileData.Uploaded + fileData.ExpiresIn)):
		if fileData.HideAfterLimitExceeded:
			return render_template("no_such_file.html")
		return render_template("limit_exceeded.html")

	return render_template("path_information.html", data=fileData)

@app.route("/<path>.<ext>")
@app.route("/<path>/actual")
@app.route("/<path>/actual.<ext>")
@check_if_path_is_valid(model.Path)
def path_transmit(path, fileData):
	if not session.get("user_id") and \
			((fileData.DownloadLimit is not None and fileData.Downloaded >= fileData.DownloadLimit) or \
			(fileData.ExpiresIn is not None and time.time() > fileData.Uploaded + fileData.ExpiresIn)):
		if fileData.HideAfterLimitExceeded:
			return render_template("no_such_file.html")
		return render_template("limit_exceeded.html")

	fileData.Downloaded = model.Path.Downloaded + 1

	geoipISOCode = "-"
	if app.config.get("ENABLE_GEOIP", False):
		try:
			geoipISOCode = addon.geoipGetCountry(request.remote_addr)
		except:
			import traceback
			print traceback.format_exc()
		
	db.session.add(model.History(path, request.remote_addr, int(time.time()), 
		request.user_agent.string, request.referrer, geoipISOCode))

	db.session.commit()

	return file.transmit(fileData.ActualName, fileData.File.StoredPath)

@app.route("/<path>/analyze")
@login_required
@check_if_path_is_valid(model.Path)
def path_analyze(path, fileData):
	fileHistory = model.History.query.filter(model.History.Path == path).order_by(model.History.Time.desc()).all()
	return render_template("path_analyze.html", path=fileData, history=fileHistory)

@app.route("/<path>/modify")
@login_required
@check_if_path_is_valid(model.Path)
def path_modify(path, fileData):
	if "downloaded" in request.form:
		fileData.Downloaded = request.form["downloaded"]
	if "download_limit" in request.form:
		fileData.DownloadLimit = request.form["download_limit"]
	if "hide_after_limit_exceeded" in request.form:
		fileData.HideAfterLimitExceeded = True if request.form["hide_after_limit_exceeded"] else False
	if "group" in reqeust.form:
		fileData.Group = request.form["group"]

	db.session.commit()

	return json.dumps({"result": True})

@app.route("/<path>/delete")
@login_required
@check_if_path_is_valid(model.Path)
def path_delete(path, fileData):
	try:
		if request.args.get("with_file", False):
			model.Path.query.filter(model.Path.FileNo == fileData.FileNo).delete()
			model.File.query.filter(model.File.No == fileData.FileNo).delete()
		else:
			model.Path.query.filter(model.Path.Path == path).delete()
		db.session.commit()
		return redirect(url_for("overview"))
	except:
		return traceback.format_exc()

# File related

@app.route("/file/<no>")
@login_required
@check_if_file_is_valid()
def file_information(no, fileData):
	return render_template("file_information.html", data=fileData)

@app.route("/file/<no>/actual")
@login_required
@check_if_file_is_valid()
def file_transmit(no, fileData):
	return file.transmit("File_%s"%(no), fileData.StoredPath)

@app.route("/file/<no>/delete")
@login_required
@check_if_file_is_valid()
def file_delete(no, fileData):
	# TODO: If "include_path" exists in request.args, delete all paths related to this file
	return abort(501)

