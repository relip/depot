Depot
=====

Depot is a simple Flask-based file sharing platform for individual use.

**HTML templates are still work in progress**

**IE9 AND EARLIER ARE NOT SUPPORTED**

See `dev` branch for WiP HTML templates.

## Features

- Expiration date
- Limiting number of downloads
- Deleting or hiding after expired
- Grouping files
- Compressing files from specific group 
- API capabilities

## Requirements

```
SQLAlchemy
Flask
Flask-Login
Flask-Bcrypt
```

## Installation

1. `pip install -r requirements.txt`
2. `cp config.py.example config.py`
3. Read and modify config.py
4. `./depot` or use uWSGI

## Nginx configuration 

In nginx.conf, put following code under `http` section.
```
server {
	 listen 80;
	server_name [domain];

	location / { try_files $uri @depot; }
	location @depot {
		include uwsgi_params;
		uwsgi_pass unix:/tmp/depot.sock;
	}
}
```
**RECOMMENDED**: If you are using XSendfile for file transfer, put following code under `server` section above. 

The importance of XSendfile is explained in `Notes` section.
```
	location /[HTTPD_BASE_DIR in config.py]/ {
		internal;
		alias /[UPLOAD_BASE_DIR in config.py]/;
	}
```
## Usage

Using Flask built-in web server:
```
./depot
```

Using [uWSGI](https://uwsgi-docs.readthedocs.org/en/latest/)(**highly recommended**):
```
uwsgi -s /tmp/depot.sock --module app --callable app --chmod-socket=777
```
If you upload large files often, it consumes long time - depends on your server specs - for retrieving file and hashing sum of it. This means python process will stuck, nothing can be uploaded until hashing gets finished. To solve this problem, set ```-p``` option to create multiple processes.

## Notes

As written in config.py.example, using flask.send_file() causes slow download speed, so set `HTTPD_USE_X_SENDFILE` to `True` if you care about download speed. 


Depot was originally planned for image uploading, some of which may have uploaded in the past. So when a file is uploaded, hash the file using MD5 and SHA1, and check if the file has already been uploaded. If has not, store it with randomly generated file name. 

Random naming makes it difficult to find directly in the terminal, using this kind of upload procedure is not suitable for uniquely named files, like videos, musics, etc. In this case, upload by other method such as FTP or SFTP, and share it with remote file browser. 
