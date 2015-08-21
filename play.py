#!/bin/python

import subprocess
import shutil
import shlex

def vlc_play(vid):
	print(vid)
	if vid['VideoFile'] is None:
		return
	cmd = shutil.which('vlc') + ' --fullscreen --play-and-exit'
	if list(vid['VideoFile']) != vid['VideoFile']:
		vids = [vid['VideoFile']]
		subfs = [vid['SubtitleFile']]
		subts = [vid['SubtitleTrack'] ]
		ats = [vid['AudioTrack'] ]
	else:
		vids = vid['VideoFile']
		l = len(vids)
		subfs = extend_to_length(vid['SubtitleFile'],l)
		subts = extend_to_length(vid['SubtitleTrack'] ,l)
		ats = extend_to_length(vid['AudioTrack'],l)

	for video, sub, subtrack, audiotrack in zip(vids, subfs, subts, ats):
		cmd += ' '+shlex.quote(video)

		if sub is not None:
			cmd += " :sub-file="+shlex.quote(sub)

		if subtrack is not None:
			cmd += ' :sub-track='+str(subtrack)

		if audiotrack is not None:
			cmd += ' :audio-track='+str(audiotrack)
	print(cmd)
	subprocess.call(cmd, shell=True)

def extend_to_length(lis, l):
	out = []
	if lis is not None and list(lis) == lis:
		if len(lis) == l:
			return lis
		out = list(lis)
	else:
		out = [lis]
	while len(out) < l:
		out.append(out[-1])
	return out
