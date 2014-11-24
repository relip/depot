# -*- coding: utf-8 -*-

import time
import traceback

from app import db
from app import app

from flask import request
from flask import make_response
from flask import send_from_directory

import common

def create_path(fileNo, fileName, method="Web", optExpiresIn=None, optDownloadLimit=None, optHideAfterLimitExceeded=None, optGroup=None):
	pathLength = 3 # default
	while True:
		try:
			newPath = Path(common.generate_random_string(int(pathLength)), fileNo,
				fileName, int(time.time()), method, request.remote_addr, optExpiresIn, optDownloadLimit,
				optHideAfterLimitExceeded, optGroup)
			db.session.add(newPath)
			db.session.commit()
			break
		except IntegrityError:
			print traceback.format_exc()
			pathLength += 0.2 # increase length every five attempts
			db.session.rollback()

	return newPath

class User(db.Model):
	__tablename__ = "User"

	No = db.Column(db.Integer, primary_key=True)
	ID = db.Column(db.String(255))
	Password = db.Column(db.String(255))
	APIKey = db.Column(db.String(32))

	def __init__(self, id, pw, apiKey):
		self.ID = id
		self.Password = pw
		self.APIKey = apiKey

	# ----- Flask-Login requirements -----

	def is_active(self):
		return True

	def is_authenticated(self):
		return True

	def is_anonymous(self):
		return False

	def get_id(self):
		return self.No

class File(db.Model):
	__tablename__ = "File"

	No = db.Column(db.Integer, primary_key=True)
	StoredPath = db.Column(db.String(255))
	MD5Sum = db.Column(db.String(32), index=True)
	SHA1Sum = db.Column(db.String(40), index=True)
	Size = db.Column(db.BigInteger)
	Paths = db.relationship("Path")

	def __init__(self, sp, m, s, size):
		self.StoredPath = sp
		self.MD5Sum = m
		self.SHA1Sum = s
		self.Size = size

class Path(db.Model):
	__tablename__ = "Path"

	Path = db.Column(db.String(255), primary_key=True, unique=True, index=True)
	ActualName = db.Column(db.String(255))
	Uploaded = db.Column(db.Integer, index=True)
	Method = db.Column(db.String(255))
	IP = db.Column(db.String(255))
	ExpiresIn = db.Column(db.Integer, nullable=True)
	DownloadLimit = db.Column(db.Integer, nullable=True)
	Downloaded = db.Column(db.Integer, default=0)
	GroupPath = db.Column(db.String(255), db.ForeignKey("Group.Path"), nullable=True, index=True)
	FileNo = db.Column(db.Integer, db.ForeignKey("File.No"))
	HideAfterLimitExceeded = db.Column(db.Boolean, default=False)

	Group = db.relationship("Group", foreign_keys=[GroupPath])
	File = db.relationship("File", foreign_keys=[FileNo])

	def __init__(self, p, fn, a, u, m, ip, e, dl, h=False, g=None):
		self.Path = p
		self.FileNo = fn
		self.ActualName = a
		self.Uploaded = u
		self.Method = m
		self.IP = ip
		self.ExpiresIn = e
		self.DownloadLimit = dl
		self.HideAfterLimitExceeded = h
		self.GroupPath = g

class Group(db.Model):
	__tablename__ = "Group"

	Path = db.Column(db.String(255), primary_key=True, index=True)
	Description = db.Column(db.Text)

	Paths = db.relationship("Path")

	def __init__(self, p, d):
		self.Path = p
		self.Description = d

class History(db.Model):
	__tablename__ = "History"

	No = db.Column(db.Integer, primary_key=True)
	Path = db.Column(db.String(255), index=True)
	IP = db.Column(db.String(255))
	Time = db.Column(db.Integer)
	UserAgent = db.Column(db.String(255))
	Referrer = db.Column(db.String(255))
	Country = db.Column(db.String(2))

	def __init__(self, p, i, t, ua, r, c):
		self.Path = p
		self.IP = i
		self.Time = t
		self.UserAgent = ua
		self.Referrer = r
		self.Country = c


class Config(db.Model):
	__tablename__ = "Config"

	Key = db.Column(db.String(255), primary_key=True)
	Value = db.Column(db.Text)

	def __init__(self, k, v):
		self.Key = k
		self.Value = v

from sqlalchemy.engine.reflection import Inspector

saInspector = Inspector.from_engine(db.engine)
saTables = saInspector.get_table_names()

if "Config" not in saTables and "Path" not in saTables:
	print "-"*100
	print "Initializing..."

	print "Creating tables..."
	db.create_all()
	print "Created tables successfully"

	tmpPW = common.generate_random_string(8)

	from flask.ext.bcrypt import generate_password_hash, check_password_hash

	print "Creating default user..."
	db.session.add(User("admin", generate_password_hash(tmpPW), common.generate_random_string(32)))
	db.session.commit()
	print "Created new user: admin / %s"%(tmpPW)

	print "-"*100

elif "Config" not in saTables:
	# Temporary patch for those who are using depot
	# version earlier than commit c0a0e1d
	db.create_all()

else: pass

