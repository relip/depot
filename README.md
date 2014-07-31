depot
=====

Depot is a simple Flask-based file sharing platform for individual use.

Supports expiration date, download limit, deleting or hiding after expired, grouping, zipping files in group and Tweetbot API.

## Requirements

```
SQLAlchemy
Flask
Flask-Login
Flask-Bcrypt
```

## Installation

1. Copy config.py.example to config.py and modify it.
2. Done!

## Usage

Using Flask built-in web server:
```
./depot
```

Using uWSGI(Recommanded):
```
uwsgi -s /tmp/depot.sock --module app --callable app --chmod-socket=777
```
If you upload large files often, it consumes long time - depends on your server specs - for retrieving file and hashing sum of it. This means python process will stuck, nothing can be uploaded until hashing gets finished. To solve this problem, set ```-p``` option to create multiple processes.
