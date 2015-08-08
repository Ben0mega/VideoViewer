#!/usr/bin/python3

import video
import os
import tkinter as tk
import tkinter.messagebox
import shutil
import subprocess
import fnmatch
import sys
import json
import collections
import mimetypes
import play
from os.path import join as path_join
from video import Video
from display import display_list
from path_utils import expand_path
from video_viewer import getConfig, CONFIG_FILE

def main():
	config = getConfig()
	for folder in findVideosFolders(config['search_path']):
		print("Working on ", folder)
		makeConfig(folder, config)

def findVideosFolders(path):
	folder = expand_path(path, os.path.abspath(os.sep))
	for dirpath, subdirs, files in os.walk(folder):
		if CONFIG_FILE in files:
			continue
		if checkForVideo(files):
			yield dirpath
	# yield folders that do not have config files
	# but have video files
	pass

def makeConfig(folder, cfg):
	dss = detectSeries(folder)
	configs = []
	print("Got ", dss)
	for video_s in dss:
		if len(video_s) == 1 or not question("Are these video files "+str(video_s)+" for one film?"):
			for video in video_s:
				t = makeVideoConfig(video, folder, cfg)
				if t is not None:
					configs.append(t)
		else:
			t = makeVideoConfig(video_s, folder, cfg, True)
			if t is not None:
				configs.append(t)
	for iso in getIso(folder):
		if question("Does "+str(iso)+" have a film on it that we have not done yet?"):
			t = makeVideoConfig(iso, folder, cfg)
			if t is not None:
				configs.append(t)
	saveConfig(configs, folder)

def saveConfig(configs, folder):
	total_path = path_join(folder, CONFIG_FILE)
	print('Saving value:', configs, total_path)
	if len(configs) == 1:
		with open(total_path, 'w') as f:
			json.dump(configs[0], f, sort_keys=True, indent=4)
	elif len(configs) > 1:
		with open(total_path, 'w') as f:
			json.dump(configs, f, sort_keys=True, indent=4)
	return


def makeVideoConfig(videoFile, folder, cfg, isList=False):
	data = toDict(videoFile, folder, isList) # returns dictionary of lists in form for json
	to_print = purify(data.dicts)
	out = videoPrompt(data, cfg)
	if out is not None:
		to_print['imdbID'] = out
		return to_print

def videoPrompt(datao, cfg):
	data = json.dumps(purify(datao.dicts), sort_keys=True, indent=4)
	root = tk.Tk()

	fdata = tk.Frame(root)
	tk.Label(fdata, text=data+'\n\n', justify=tk.LEFT).pack(side='top')
	fdata.pack(side='top')

	flines = tk.Frame(root)
	tk.Label(flines, text='IMDB ID?:').pack(side='left')
	t = tk.Entry(flines, width=20)
	t.pack(side='left')
	tk.Label(flines, text='\t(EX: tt0094025)').pack(side='left')
	flines.pack(side='top')

	fbuttons = tk.Frame(root)
	tk.Button(fbuttons, text='Play', command=makePlay(datao, cfg)).pack(side='left')
	tk.Button(fbuttons, text='Ok', command=makeClose(root, t, True)).pack(side='left')
	tk.Button(fbuttons, text='Skip', command=makeClose(root, t, False)).pack(side='left')
	fbuttons.pack(side='top')

	root.mainloop()

	if videoPrompt.toRecord:
		temp = videoPrompt.value.lstrip().rstrip()
		assert(len(temp) > 0)
		assert(temp[0:2] == 'tt')
		return temp
	# display name of file
	# have button to play
	# ask for imdbID
	# have button to skip
videoPrompt.toRecord = False
videoPrompt.value = ''

def makeClose(root, getVal, skipval):
	def f():
		videoPrompt.toRecord = skipval
		videoPrompt.value = getVal.get()
		root.destroy()
	return f

def makePlay(vid, cfg):
	def f():
		player = getattr(play, cfg['video_player']+'_play')
		player(vid)
	return f

def purify(data):
	data2 = {}
	for a in data.keys():
		if data[a] is not None:
			data2[a] = data[a]
	return data2

def toDict(files, folder, isList):
	# we need SubtitleFile, SubtitleTrack, VideoFile,
	subs = []
	subtrs = []
	if not isList:
		files = [files]
	# dead simple matching - assumes it has the same name except the extension
	for vid in files:
		for sub in getSubs(folder):
			if sub.startswith(vid[:-3]):
				subs.append(sub)
				subtrs.append(0)
				break
	if len(subs) == 0:
		subs = [None]
		subtrs = []

		for vid in files:
			if b'Subtitle' in getStreams(vid, folder):
				subtrs.append(0)
			else:
				subtrs.append(None)

	if not isList:
		files = files[0]
		subs = subs[0]
		subtrs = subtrs[0]
		return NoneDict({'VideoFile' : files, 'SubtitleFile':subs, 'SubtitleTrack':subtrs}, folder)
	return NoneDict({'VideoFile' : files, 'SubtitleFile':subs, 'SubtitleTrack':subtrs}, folder)

class NoneDict:
	def __init__(self, dicts, folder):
		self.dicts = dicts
		self.folder = folder

	def __getitem__(self, arg):
		if arg not in self.dicts.keys() or self.dicts[arg] is None:
			return None
		if arg in video.Video.PATH_ATTRS:
			return path_join(self.folder, self.dicts[arg])
		return self.dicts[arg]

def question(text):
	root = tk.Tk()
	flines = tk.Frame(root)
	tk.Label(flines, text=text).pack(side='left')
	flines.pack(side='top')

	fbuttons = tk.Frame(root)
	tk.Button(fbuttons, text='Yes', command=makeBoolClose(root, True)).pack(side='left')
	tk.Button(fbuttons, text='No', command=makeBoolClose(root, False)).pack(side='left')
	fbuttons.pack(side='top')
	root.mainloop()

	return question.retval
question.retval = False

def makeBoolClose(root, val):
	def f():
		question.retval = val
		root.destroy()
	return f

def getStreams(files, folder):
	target = path_join(folder, files)
	if shutil.which('ffprobe') is None:
		execs = 'avprobe'
	elif shutil.which('ffprobe') is not None:
		execs = 'ffprobe'
	try:
		out = subprocess.check_output([execs, target], stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError:
		if files[-4:] == '.iso':
			# I assume all isos have subtitles - vlc handles it gracefully
			return [b'Video', b'Subtitle']
		return

	outlist = []
	for line in out.split(b"\n"):
		lines = line.lstrip()
		if lines.startswith(b'Stream'):
			yield getStreamType(lines)

def getStreamType(lines):
	options = [b'Video', b'Subtitle', b'Audio', b'Attachment']
	choices = []
	for a in options:
		try:
			choices.append((lines.index(a),a))
		except ValueError:
			pass
	my_choice = min(choices)
	return my_choice[1]

def getSubs(folder):
	extensions = ['.sub', '.srt']
	for files in os.listdir(folder):
		if files[-4:] in extensions:
			yield files

def getIso(folder):
	for files in os.listdir(folder):
		if files[-4:] == '.iso':
			yield files

def detectSeries(folder):
	todo = [a for a in getVideoFiles(os.listdir(folder))]
	print(todo)
	assert(len(todo) > 0)
	todo.sort()
	current = []
	total = []
	for a in todo:
		if isSeriesName(current, a):
			current.append(a)
		else:
			total.append(current)
			current = []
	if len(current) != 0:
		total.append(current)
	return total

def isSeriesName(cur, nex):
	if len(cur) == 0:
		return True
	if len(nex) != len(cur[-1]):
		return False
	for let1, let2 in zip(cur[-1], nex):
		if let1 == let2:
			continue
		if ord(let1) +1 != ord(let2):
			return False
	return True

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

if __name__ == "__main__":
	main()
