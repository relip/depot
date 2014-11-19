# -*- coding: utf-8 -*-

import traceback

from app import app

# -------------------------------------------------- GEOIP
geipipReader = None

def geoipInit():
	if app.config.get("ENABLE_GEOIP", False):
		try:
			import geoip2.database

			global geoipReader
			geoipReader = geoip2.database.Reader(app.config.get("GEOIP_DATABASE_PATH", ""))
		except:
			# temporary
			print traceback.format_exc()
			app.config["ENABLE_GEOIP"] = False
			#logging.warn("geoip2 module is missing. Disabling GeoIP feature.")

def geoipGetCountry(ip):
	app.config.get("ENABLE_GEOIP", False)
	try:
		return geoipReader.city(ip).country.iso_code
	except:
		print traceback.format_exc()
		return "-"


# -------------------------------------------------- INIT
def init():
	# ------------------------------ GEOIP
	geoipInit()
