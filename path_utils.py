#!/bin/python
import os.path

def expand_path(path, dirs):
	path = os.path.expandvars(path)
	path = os.path.expanduser(path)
	return os.path.normpath(os.path.join(dirs, path))

