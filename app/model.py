# -*- coding: utf-8 -*-

from app import db

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
	ExpiresIn = db.Column(db.Integer, nullable=True)
	DownloadLimit = db.Column(db.Integer, nullable=True)
	Downloaded = db.Column(db.Integer, default=0)
	GroupPath = db.Column(db.String(255), db.ForeignKey("Group.Path"), nullable=True, index=True)
	FileNo = db.Column(db.Integer, db.ForeignKey("File.No"))
	HideAfterLimitExceeded = db.Column(db.Boolean, default=False)

	Group = db.relationship("Group", foreign_keys=[GroupPath])
	File = db.relationship("File", foreign_keys=[FileNo])

	def __init__(self, p, fn, a, u, e, dl, h=False, g=None):
		self.Path = p
		self.FileNo = fn
		self.ActualName = a
		self.Uploaded = u
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


db.create_all()
