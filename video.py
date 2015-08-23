#!/bin/python
from path_utils import expand_path
from os.path import join as path_join
from os.path import exists as path_exists
from os.path import relpath
from PIL import Image, ImageTk
import os
import urllib.request
import json

class Video:
	CACHE_FOLDER_NAME=".cache"
	CACHE_JSON_NAME="cache.json"
	CACHE_POSTER_NAME="poster.jpg"
	PATH_ATTRS=['VideoFile', 'SubtitleFile', 'PosterFile']
	attrs=set()

	def __init__(self, content, folder):
		self.attrs = content
		self.original_keys = content.keys()
		self.folder = folder
		self.imdbID=self.attrs['imdbID']
		self.getAdvancedAttrs()
		self.series = None
		self.images = {}

	def _getCacheFolder(self):
		return path_join(self.folder, Video.CACHE_FOLDER_NAME)

	def _getCacheFile(self):
		return path_join(self._getCacheFolder(), self.imdbID+'.'+Video.CACHE_JSON_NAME)

	def _getCachePosterFile(self):
		return path_join(self._getCacheFolder(), self.imdbID+'.'+Video.CACHE_POSTER_NAME)

	def getSeries(self):
		if self.series is None and self.hasSeries():
			series = self['seriesID']
			self.series = Video({'imdbID': series}, self.folder)
		return self.series

	def hasSeries(self):
		return  'seriesID' in self.attrs.keys()

	def getId(self):
		return self['imdbID']

	def getPosterOfSize(self, x, y):
		if (x,y) not in self.images.keys():
			image = Image.open(self['PosterFile']).resize((x, y), Image.ANTIALIAS)
			photo = ImageTk.PhotoImage(image)
			self.images[(x,y)] = photo
		return self.images[(x,y)]

	def getAdvancedAttrs(self):
		cache_file = self._getCacheFile()
		if not path_exists(self._getCacheFolder()):
			os.mkdir(self._getCacheFolder())

		if not path_exists(cache_file):
			try:
				print("Fetching cache of imdb data!")
				urllib.request.urlretrieve('http://www.omdbapi.com/?i=%s&plot=full&r=json&tomatoes=true' % self.imdbID, cache_file)
			except:
				pass

		with open(cache_file) as f:
			self.attrs = override_join(json.loads(f.read()), self.attrs)

		if 'PosterFile' not in self.attrs.keys() or not path_exists(self.attrs['PosterFile']):
			cache_poster_path = self._getCachePosterFile()
			success = True
			if not path_exists(cache_poster_path):
				try:
					print("Fetching cache of imdb poster!")
					urllib.request.urlretrieve(self.attrs['Poster'], cache_poster_path)
				except:
					success=False
			if success:
				self.attrs['PosterFile'] = relpath(cache_poster_path, self.folder)
		Video.addAttrs(self.attrs.keys())

	def __getitem__(self, arg):
		if arg in Video.PATH_ATTRS:
			if arg not in self.attrs.keys():
				if self.hasSeries():
					return self.getSeries()[arg]
				return None
			stuff = self.attrs[arg]
			# can have multiple files for Videos
			# or for subtitles
			if list(stuff) == stuff:
				data = []
				for a in stuff:
					data.append(expand_path(a, self.folder))
				return data
			return expand_path(self.attrs[arg], self.folder)
		tmp = self.attrs.get(arg,None)
		if tmp is None and self.hasSeries():
			return self.getSeries()[arg]
		return tmp

	@classmethod
	def addAttrs(cls, attrs):
		for a in attrs:
			if a not in cls.attrs:
				cls.attrs.add(a)

	@classmethod
	def getAttrs(cls):
		return cls.attrs

	def __str__(self):
		data = {}
		for a in Video.getAttrs():
			data[a] = self[a]
		return json.dumps(data, sort_keys=True, indent=4)

	def __repr__(self):
		return str(self)

	def __del__(self):
		cache_file = self._getCacheFile()

		# dont save items specified in config.json
		data = {}
		for key in self.attrs.keys():
			if key not in self.original_keys:
				tmp = self.attrs[key]
				if key in Video.PATH_ATTRS:
					tmp = self[key]
					tmp = relpath(tmp, self.folder)
				data[key] = tmp
		with open(cache_file, 'w') as outfile:
			json.dump(data, outfile, sort_keys=True, indent=4)

def override_join(original, override):
	for key in override.keys():
		original[key] = override[key]
	return original
