#!/usr/bin/python3

import traceback
import os
import shutil
import subprocess
import fnmatch
import sys
import json
import collections
import mimetypes
from os.path import join as path_join
from video import Video
from display import display_list
from path_utils import expand_path

PROG_NAME = 'VideoViewer'
CONFIG_PATH = path_join(os.getenv('XDG_CONFIG_HOME', path_join(os.environ['HOME'], '.config')), PROG_NAME, 'config.json')
CONFIG_FILE="config.json"
DEFAULT_CONFIG={
		'search_path':path_join(os.environ['HOME'],'Videos'),
		'columns':['PosterFile', 'Title', 'Plot', 'Runtime', "Rated", "Genre", "Actors", "Director"],
		'video_player': 'vlc'
	}

def main():
	config = getConfig()
	database = getVideos(config)
	new_config = display_list(database, config)
	saveConfig(new_config)

def getConfig():
	if os.path.exists(CONFIG_PATH):
		with open(CONFIG_PATH) as f:
			return json.loads(f.read())
	return DEFAULT_CONFIG.copy()

def saveConfig(cfg):
	if cfg == DEFAULT_CONFIG:
		return
	if not os.path.exists(os.path.dirname(CONFIG_PATH)):
		os.mkdir(os.path.dirname(CONFIG_PATH))
	with open(CONFIG_PATH, 'w') as outfile:
		json.dump(cfg, outfile, sort_keys=True, indent=4)

def getVideos(cfg):
	database = []
	for data_path in findDBs(cfg['search_path']):
		database.extend(parseVideos(data_path))
	return database

def findDBs(top_folder):
	folder = expand_path(top_folder, os.path.abspath(os.sep))
	for dirpath, subdirs, files in os.walk(folder):
		if CONFIG_FILE in files:
			yield path_join(folder, dirpath, CONFIG_FILE)

def parseVideos(paths):
	for a in jsonObjectParse(paths):
		for key in a.keys():
			parseVideos.keys.add(key)
		vids = a.get('VideoFile', None)

		# skip "video" with no file
		if vids is None:
			continue
		if list(vids) == vids and any(not os.path.exists(expand_path(b, os.path.dirname(paths))) for b in vids):
			continue
		if list(vids) != vids and not os.path.exists(expand_path(vids, os.path.dirname(paths))):
			continue

		yield Video(a, os.path.dirname(paths))
parseVideos.keys=set()

def jsonObjectParse(paths):
	try:
		with open(paths) as f:
			strs = f.read()
			# support for empty config files to silence querying for it
			if len(strs) == 0:
				return
			v = json.loads(strs)
		if isinstance(v, collections.Mapping):
			yield v
		elif isinstance(v, (str,bytes)) or v is None:
			print("Malformed file!", paths)
			assert(False)
		else:
			for a in v:
				yield a
	except:
		print(traceback.format_exc())

if __name__ == "__main__":
	main()
