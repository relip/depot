# -*- coding: utf-8 -*-

import urlparse
import datetime
import math

def convertTime(value, format='%Y/%m/%d %H:%M:%S'):
	return datetime.datetime.fromtimestamp(value).strftime(format)

def convertSize(size):
	if size <= 0:
		return "0B"
	size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
	i = int(math.floor(math.log(size,1024)))
	p = math.pow(1024,i)
	s = round(int(size)/p,2)
	if s > 0:
		return '%s%s' % (s,size_name[i])
	else:
		return "0B"

urljoin = urlparse.urljoin

__all__ = ["convertTime", "convertSize", "urljoin"]
