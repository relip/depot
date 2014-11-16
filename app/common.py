# -*- coding: utf-8 -*-

import string
import random

def generate_random_string(n):
	return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(n))
