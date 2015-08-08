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
	to_fix = []
	folder = expand_path(top_folder, os.path.abspath(os.sep))
	for dirpath, subdirs, files in os.walk(folder):
		if CONFIG_FILE in files:
			yield path_join(folder, dirpath, CONFIG_FILE)
		elif checkForVideo(files):
			to_fix.append((dirpath, files))
	if len(sys.argv) > 1:
		for dirpath, files in to_fix:
			out = makeConfig(folder, dirpath, files)
			if out is not None:
				yield out

def makeConfig(folder, dirs, files):
	files = list(files)
	files.sort()
	configs = []
	for vf in getVideoFiles(files):
		config = makeConfigPerVideo(dirs, files, vf, folder)
		if len(config.keys()) > 0:
			configs.append(config)
	total_path = path_join(folder, dirs, CONFIG_FILE)
	print('Saving value:', configs)
	if len(configs) == 1:
		with open(total_path, 'w') as f:
			json.dump(configs[0], f, sort_keys=True, indent=4)
	elif len(configs) > 1:
		with open(total_path, 'w') as f:
			json.dump(configs, f, sort_keys=True, indent=4)
	else:
		return
	return total_path

def makeConfigPerVideo(dirs, files, vf, folder):
	if shutil.which('ffprobe') is None:
		subprocess.call(['avprobe', path_join(folder, dirs, vf)])
	elif shutil.which('ffprobe') is not None:
		subprocess.call(['ffprobe', path_join(folder, dirs, vf)])
	print("\n\nIn ", dirs, " working on ", vf)
	print("Other files are: ", files)
	config = {}
	keys = list(parseVideos.keys)
	keys.sort()
	for key in keys:
		yorn = readGlobString(files, key)
		if len(yorn) > 0:
			config[key] = yorn
	return AddOrFixConfig(config, dirs, files, vf)

def AddOrFixConfig(config, dirs, files, vf):
	print("\nIn ", dirs, " working on ", vf)
	print("Other files are: ", files)
	print("\nConfig to save: ", config, '\n')
	key = input('\nSpecify key to fix or additional key to add:')
	while len(key) > 0:
		yorn = readGlobString(files, key)
		if len(yorn) > 0:
			config[key] = yorn
		elif key in config.keys():
			del config[key]
		print("Config to save: ", config)
		key = input('\nSpecify key to fix or additional key to add:')
	return config

def readGlobString(files, key):
	strs = input("\nGlob value for "+key+"?:")
	matched = fnmatch.filter(files, strs)
	while len(matched) > 1:
		strs = input("Unable to disambiguate the match ("+str(matched)+"), please try again:")
		matched = fnmatch.filter(files, strs)
	if len(matched) == 0:
		return strs
	return matched[0]

def checkForVideo(files):
	try:
		next(getVideoFiles(files))
		return True
	except StopIteration:
		pass
	return False

def getVideoFiles(files):
	for fil in files:
		types, encodes = mimetypes.guess_type(fil, False)
		if types is not None and 'video' in types:
			yield fil

def parseVideos(paths):
	for a in jsonObjectParse(paths):
		for key in a.keys():
			parseVideos.keys.add(key)
		vids = a.get('VideoFile', None)
		if vids is None:
			continue
		if list(vids) == vids and any(not os.path.exists(expand_path(b, os.path.dirname(paths))) for b in vids):
			continue
		if list(vids) != vids and  not os.path.exists(expand_path(vids, os.path.dirname(paths))):
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
