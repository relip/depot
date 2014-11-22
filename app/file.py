# -*- coding: utf-8 -*-

import os
import hashlib
import mimetypes
import json

from flask import request
from flask import make_response
from flask import send_file
from flask import render_template

from sqlalchemy.exc import IntegrityError

from app import app
from app import db

import model
import common

def _empty_string_to_none(s):
	return s if s != "" else None

def store_local(normalizedPath):
	normalizedFullPath = os.path.join(app.config["UPLOAD_BASE_DIR"], normalizedPath)

	if not os.path.isfile(normalizedFullPath):
		return json.dumps({"result": False, "message": "Given path is not a file"})

	# We don't check hashsum of local files since it has the possibility of modifying its content, 
	# which means hashing is meaningless, and has the possibility of pointing a File object 
	# that has same hashsum but different File.StoredPath.

	fileSize = os.stat(normalizedFullPath).st_size
	fileData = model.File(normalizedPath, "1", "1", fileSize)
	db.session.add(fileData)
	db.session.commit()

	optExpiresIn = _empty_string_to_none(request.form.get("expires_in", None))
	optDownloadLimit = _empty_string_to_none(request.form.get("download_limit", None))
	optHideAfterLimitExceeded = not not request.form.get("hide_after_limit_exceeded", False)
	optGroup = _empty_string_to_none(request.form.get("group", None))

	newPath = model.create_path(fileData.No, os.path.basename(normalizedFullPath), optExpiresIn, optDownloadLimit,
		optHideAfterLimitExceeded, optGroup)

	return json.dumps({"result": True, "path": newPath.Path})

def store(fp):
	realFilename = fp.filename
	md5sum = _hash_file(fp, hashlib.md5())
	sha1sum = _hash_file(fp, hashlib.sha1())
	fp.seek(0)

	fileData = model.File.query.filter(model.File.MD5Sum == md5sum,
		model.File.SHA1Sum == sha1sum).first()

	if not fileData:
		while True:
			newFilename = common.generate_random_string(32)
			if not os.path.exists(os.path.join(app.config['UPLOAD_FULL_DIRECTORY'], newFilename)):
				break
		fullPath = os.path.join(app.config['UPLOAD_FULL_DIRECTORY'], newFilename)
		fp.save(fullPath)
		fileSize = os.stat(fullPath).st_size
		fileData = model.File(os.path.join(app.config["UPLOAD_DIRECTORY"], newFilename),
			md5sum, sha1sum, fileSize)
		db.session.add(fileData)
		db.session.commit()

	# FIXME: Set to None if the value is empty string which cause exception when checking for settings
	optExpiresIn = _empty_string_to_none(request.form.get("expires_in", None))
	optDownloadLimit = _empty_string_to_none(request.form.get("download_limit", None))
	optHideAfterLimitExceeded = not not request.form.get("hide_after_limit_exceeded", False)
	optGroup = _empty_string_to_none(request.form.get("group"))

	newPath = model.create_path(fileData.No, realFilename, optExpiresIn, optDownloadLimit,
		optHideAfterLimitExceeded, optGroup)

	return json.dumps({"result": True, "path": newPath.Path})

# http://stackoverflow.com/questions/3431825/generating-a-md5-checksum-of-a-file
def _hash_file(afile, hasher, blocksize=65536):
	afile.seek(0)
	buf = afile.read(blocksize)
	while len(buf) > 0:
		hasher.update(buf)
		buf = afile.read(blocksize)
	return hasher.hexdigest()

def transmit(fileName, storedPath):
	if not os.path.isfile(os.path.join(app.config["UPLOAD_BASE_DIR"], storedPath)):
		return render_template("no_such_file.html")
	if app.config.get("HTTPD_USE_X_SENDFILE", False):
		response = make_response()
		response.headers["Content-Disposition"] = "inline; filename=\"%s\""%(fileName.encode("utf-8"))
		response.headers["Content-Type"] = mimetypes.guess_type(fileName)[0]
		httpdType = app.config.get("HTTPD_TYPE", "nginx")

		if httpdType == "apache" or httpdType == "lighttpd":
			response.headers["X-Sendfile"] = os.path.join(app.config["UPLOAD_BASE_DIR"], storedPath.encode("utf-8"))
		else: # nginx and others
			response.headers["X-Accel-Redirect"] = os.path.join(app.config.get("HTTPD_BASE_DIR", "/"), storedPath.encode("utf-8"))

		return response
	else:
		response = make_response(send_file(os.path.join(app.config["UPLOAD_BASE_DIR"], storedPath),
			mimetype=mimetypes.guess_type(fileName)[0]))
		response.headers["Content-Disposition"] = "inline; filename=\"%s\""%(fileName.encode("utf-8"))
		return response

