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

from flask import render_template 
from flask import send_from_directory
from flask import make_response
from flask import request
from flask import abort
from flask import session
from flask import url_for
from flask import redirect
from flask import send_file
from werkzeug.utils import secure_filename
from flask.ext.login import LoginManager
from flask.ext.login import login_required
from flask.ext.login import login_user
from flask.ext.login import logout_user
from flask.ext.login import current_user
from flaskext.bcrypt import generate_password_hash, check_password_hash

from app import app
from app import db

import model

login_manager = LoginManager()
login_manager.init_app(app)

def _store_file(fp):
	realFilename = secure_filename(fp.filename)
	md5sum = hashfile(fp, hashlib.md5())
	fp.seek(0)
	sha1sum = hashfile(fp, hashlib.sha1())
	fp.seek(0)

	fileData = model.File.query.filter(model.File.MD5Sum == md5sum, 
		model.File.SHA1Sum == sha1sum).first()

	if not fileData:
		while True:
			newFilename = generateRandomString(32)
			if not os.path.exists(os.path.join(app.config['UPLOAD_FULL_DIRECTORY'], newFilename)):
				break
		fp.save(os.path.join(app.config['UPLOAD_FULL_DIRECTORY'], newFilename))

		fileData = model.File(os.path.join(app.config["UPLOAD_DIRECTORY"], newFilename), 
			md5sum, sha1sum)
		db.session.add(fileData)
		db.session.flush()

	pathLength = 3 # default
	while True:
		try:
			newPath = model.Path(generateRandomString(int(pathLength)), fileData.No, 
				realFilename, request.form.get("download_limit", 0), 
				request.form.get("hide_after_limit_exceeded", False), request.form.get("group", None))
			db.session.add(newPath)
			db.session.commit()
			break
		except:
			print traceback.format_exc()
			pathLength += 0.2 # increase length every five attempts 
			db.session.rollback()

	return json.dumps({"result": True, "path": newPath.Path})

# http://stackoverflow.com/questions/3431825/generating-a-md5-checksum-of-a-file
def hashfile(afile, hasher, blocksize=65536):
	buf = afile.read(blocksize)
	while len(buf) > 0:
		hasher.update(buf)
		buf = afile.read(blocksize)
	return hasher.hexdigest()

def generateRandomString(n):
	return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(n))

@login_manager.user_loader
def load_user(uid):
	return model.User.query.filter(model.User.No == int(uid)).first()

@login_manager.unauthorized_handler
def unauthorized():
	return abort(404)

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


@app.teardown_appcontext
def shutdown_session(exception=None):
	db.session.remove()

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
	if request.method == 'POST':
		fp = request.files["file"]
		return _store_file(fp)

	else:
		return render_template("upload.html")

@app.route("/api/tweetbot", methods=["GET", "POST"])
def api_tweetbot():
	if not request.form["source"].startswith("Tweetbot for"):
		return abort(404)
	elif not model.User.query.filter(model.User.APIKey == request.args["api_key"]).first():
		return abort(403)
	else:
		print request.files
		fp = request.files["media"]
		fileName, fileExtension = os.path.splitext(fp.filename)
		result = json.loads(_store_file(request.files["media"]))
		return json.dumps({"url": request.url_root + result["path"] + "/actual" + fileExtension})

@app.route("/groups")
@login_required
def groups():
	return render_template("groups.html", groups=model.Group.query.all())

@app.route("/groups/create", methods=["GET", "POST"])
@login_required
def create_group():
	if request.mothod == "POST" and "paths" in request.form:
		pathLength = 3 # default
		while True:
			try:
				groupPath = generateRandomString(int(pathLength))
				db.session.add(model.Group(groupPath, 
					request.form.get("description", "")))
				db.session.flush()
				break
			except:
				db.session.rollback()
				pathLength += 0.2

		result = {}
		for p in request.form["paths"].split(","):
			p = p.strip()
			fileData = model.Path.query.filter(model.Path.Path == p).first()

			if not fileData:
				result.update({p: False})

			fileData.Group = groupPath

			db.session.commit()

			result.update({p: True})

		return json.dumps({"path": groupPath, "result": result})

	return render_template("groups_create.html")

@app.route("/group/<path>")
@check_if_path_is_valid(model.Group)
def group_information(path, groupData):
	return render_template("group.html", groupData=groupData)

@app.route("/group/<path>/delete")
@login_required
@check_if_path_is_valid(model.Group)
def group_delete(path, groupData):
	try:
		groupQuery = model.Group.query.filter(model.Group.Path == path)
		groupQuery.delete()
		return redirect(url_for("overview"))
	except:
		return traceback.format_exc()

@app.route("/group/<path>/modify")
@login_required
@check_if_path_is_valid(model.Group)
def group_modify(path, groupData):
	if "description" in request.form:
		groupData.Description = request.form["description"]
	db.session.commit()

	return json.dumps({"result": True})

@app.route("/signin", methods=["GET", "POST"])
def signin():
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
	if not app.config["ENABLE_SIGNUP"]:
		return abort(404)

	elif (request.method == "POST" and
		request.form["id"] and request.form["password"]):
		u = model.User(request.form["id"], generate_password_hash(request.form["password"]), generateRandomString(32))
		db.session.add(u)
		db.session.commit()
		return redirect(url_for("overview"))
	else:
		return render_template("signup.html")

@app.route("/overview")
@login_required
def overview():
	uinfo = load_user(session["user_id"])
	return render_template("overview.html", paths=model.Path.query.all(), userInfo=uinfo)

@app.route("/<path>")
@check_if_path_is_valid(model.Path)
def file_information(path, fileData):
	if fileData.Downloaded >= fileData.DownloadLimit and fileData.DownloadLimit != 0:
		if fileData.HideAfterLimitExceeded:
			return reder_template("no_such_file.html")
		return render_template("limit_exceeded.html")

	return render_template("file_information.html", data=fileData)

@app.route("/<path>/actual")
@app.route("/<path>/actual.<ext>")
@check_if_path_is_valid(model.Path)
def file_transmit(path, fileData):
	if fileData.Downloaded >= fileData.DownloadLimit and fileData.DownloadLimit != 0:
		if fileData.HideAfterLimitExceeded:
			return reder_template("no_such_file.html")
		return render_template("limit_exceeded.html")

	fileData.Downloaded = model.Path.Downloaded + 1
	db.session.add(model.History(path, request.remote_addr, int(time.time()), 
		request.user_agent.string, request.referrer, "-"))

	db.session.commit()

	if app.config.get("HTTPD_USE_X_SENDFILE", False):
		response = make_response()
		response.headers["Content-Disposition"] = "inline; filename=\"%s\""%(fileData.ActualName)

		httpdType = app.config.get("HTTPD_TYPE", "nginx")

		if httpdType == "apache" or httpdType == "lighttpd":
			response.headers["X-Sendfile"] = os.path.join(app.config["UPLOAD_BASE_DIR"], fileData.File.StoredPath)
		else: # nginx and others
			response.headers["X-Accel-Redirect"] = os.path.join(app.config.get("HTTPD_BASE_DIR", "/"), fileData.File.StoredPath)
		return response
	else:
		print fileData.ActualName
		response = make_response(send_file(os.path.join(app.config["UPLOAD_BASE_DIR"], fileData.File.StoredPath),
			mimetype=mimetypes.guess_type(fileData.ActualName)[0]))
		response.headers["Content-Disposition"] = "inline; filename=\"%s\""%(fileData.ActualName)
		return response

@app.route("/<path>/analyze")
@login_required
@check_if_path_is_valid(model.Path)
def file_analyze(path, fileData):
	fileHistory = model.History.query.filter(model.History.Path == path).all()
	return render_template("file_analyze.html", path=fileData, history=fileHistory)

@app.route("/<path>/modify")
@login_required
@check_if_path_is_valid(model.Path)
def file_modify(path, fileData):
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
def file_delete(path, fileData):
	try:
		model.File.query.filter(model.File.Path == path).delete()
		db.session.commit()
		return redirect(url_for("overview"))
	except:
		return traceback.format_exc()


