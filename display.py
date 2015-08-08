import tkinter as tk
from PIL import Image, ImageTk
import play
import functools
from video import Video

def display_list(db, cfg):
	foo = VideoDisplay(db, cfg)
	foo.run()
	return foo.getConfig()

class VideoDisplay:
	SERIES_ID='seriesID'
	def __init__(self, db, cfg):
		self.cfg = cfg
		series = {}
		for a in db:
			if a[VideoDisplay.SERIES_ID] is not None and a[VideoDisplay.SERIES_ID] not in series.keys():
				series[a[VideoDisplay.SERIES_ID]] = a.getSeries()
		self.db = db.copy()
		self.db.extend(series.values())
		self.root = tk.Tk()
		self.searchFrame = tk.Frame(self.root, background="#D9D9D9")
		self.searchFrame.pack(side="top")
		self.canvas = tk.Canvas(self.root, borderwidth=0, background="#ffffff")

		self.canvas.bind_all("<MouseWheel>", self._on_ymousewheel)
		self.canvas.bind_all("<4>", self._on_ymousewheel)
		self.canvas.bind_all("<5>", self._on_ymousewheel)

		self.canvas.bind_all("<Shift-MouseWheel>", self._on_xmousewheel)

		self.canvas.bind_all("<ButtonPress-1>", self.startMove)
		self.canvas.bind_all("<ButtonRelease-1>", self.stopMove)
		self.canvas.bind_all("<B1-Motion>", self.onMotion)

		self.setupScrollbars()

		self.canvas.pack(side="bottom", fill="both", expand=True)

		self.sortKey="Title"
		self.sortDir=1

		self.makeHeader()

	def getConfig(self):
		return self.cfg

	def run(self):
		self.refresh()
		self.root.mainloop()

	def clear(self):
		self.canvas.delete('all')
		self.frame = tk.Frame(self.canvas, background="#ffffff")
		self.canvas.create_window((4,4), window=self.frame, anchor="nw")
		self.frame.bind("<Configure>", self.onFrameConfigure)

	def makeHeader(self):
		tk.Button(self.searchFrame, text="Preferences", command=self.showPreferences).pack(side="left")

		tk.Label(self.searchFrame, text="Search:", bg="#D9D9D9", padx=10).pack(side="left")

		self.searchEntry = tk.Entry(self.searchFrame, width=40)
		self.searchEntry.delete(0, tk.END)
		self.searchEntry.pack(side="left", fill="x")

		tk.Button(self.searchFrame, text="Clear", command=self.clearSearch).pack(side="right")
		tk.Button(self.searchFrame, text="Filter", command=self.refresh).pack(side="right")

	def showPreferences(self):
		self.prefWin = tk.Toplevel(self.root)
		frame = tk.Frame(self.prefWin)
		frame.pack(side='top')
		label = tk.Label(frame, text='Search Path for Videos (takes effect on restart of program): ')
		label.pack(side="left")
		self.videoSearchEntry = tk.Entry(frame, width=40)
		self.videoSearchEntry.delete(0, tk.END)
		self.videoSearchEntry.insert(0, self.cfg['search_path'])
		self.videoSearchEntry.pack(side="left", fill="x")
		tk.Button(frame, text='Update', command=self.updateSearchPath).pack(side='left')

		frame2 = tk.Frame(self.prefWin)
		frame2.pack(side='top')
		label = tk.Label(frame2, text='Columns: ')
		label.pack(side="left")
		self.colEntry = tk.Entry(frame2, width=40,)
		self.colEntry.delete(0, tk.END)
		self.colEntry.insert(0, toSimpleListStr(self.cfg['columns']))
		self.colEntry.pack(side="left", fill="x")
		tk.Button(frame2, text='Update', command=self.updateColumns).pack(side='left')

		frame2ish = tk.Frame(self.prefWin)
		frame2ish.pack(side='top')
		tk.Label(frame2ish, text="Available Columns:").pack(side='left')
		tk.Label(frame2ish, text=toSimpleListStr(getAvailableColumns(), True),
				wraplength=350
				).pack(side='left')

		frame3 = tk.Frame(self.prefWin)
		frame3.pack(side='top')
		label = tk.Label(frame3, text='Video Player: ')
		label.pack(side="left")
		self.player = tk.StringVar(self.root)
		self.player.set(self.cfg['video_player'])
		self.player.trace('w', self.changePlayer)
		tk.OptionMenu(frame3, self.player, *getPlayers()).pack(side='left')

	def changePlayer(self, *args):
		self.cfg['video_player'] = self.player.get()
		self.refresh()

	def updateSearchPath(self):
		self.cfg['search_path'] = self.videoSearchEntry.get()

	def updateColumns(self):
		self.cfg['columns'] = fromSimpleListStr(self.colEntry.get())
		self.refresh()

	def clearSearch(self):
		self.searchEntry.delete(0, 'end')
		self.refresh()

	def refresh(self):
		self.clear()
		self.canvas.yview_moveto(0)
		self.canvas.xview_moveto(0)
		if self.searchEntry.get() != "":
			self.displaying = self.performSearch()
		else:
			self.displaying = [a for a in self.db]

		# this is slow
		self.displaying.sort(key=functools.cmp_to_key(self.videoCmp))

		self.display_sort_column_heads(0)
		ro=1
		for line in self.displaying:
			self.display_video(line,  ro)
			ro+=1

	def performSearch(self):
		out = []
		gen_str, col_search = parseSearch(self.searchEntry.get())
		for vid in self.db:
			for col in self.cfg['columns']:
				vidc = no_none_get(vid, col, 'N/A')
				if col in col_search.keys() and col_search[col] in vidc:
					out.append(vid)
					break
				if gen_str is not None and gen_str in vidc:
					out.append(vid)
					break
		return out

	def videoCmp(self, a, b):
		# always put series entries before the series values
		# all the series stuff is a hack right now
		if a[VideoDisplay.SERIES_ID] == b['imdbID']:
			return 1
		elif b[VideoDisplay.SERIES_ID] == a['imdbID']:
			return -1

		# put all items in a series together
		# if we are not part of the same series (or both not part of the series) compare with series item
		if a[VideoDisplay.SERIES_ID] != b[VideoDisplay.SERIES_ID]:
			if a[VideoDisplay.SERIES_ID] is not None:
				a = a.getSeries()
			if b[VideoDisplay.SERIES_ID] is not None:
				b = b.getSeries()

		ak = no_none_get(a,self.sortKey,"N/A")
		bk = no_none_get(b,self.sortKey,"N/A")
		if ak==bk:
			return 0
		if ak > bk:
			return self.sortDir
		return -1*self.sortDir

	def display_sort_column_heads(self, ro):
		col = 0
		for column in self.cfg['columns']:
			name = column
			if name == self.sortKey:
				if self.sortDir == 1:
					name += "↓"
				else:
					name += "↑"
			lb = tk.Label(self.frame, text=name)
			lb.bind("<Button-1>", make_toggle_key(self, column))
			lb.grid(row=ro, column=col, sticky=tk.W+tk.E+tk.N+tk.S)
			col+=1

	def toggleKey(self, key):
		if key == self.sortKey:
			self.sortDir *= -1
		else:
			self.sortKey = key
			self.sortDir = 1
		self.refresh()

	def display_video(self, line, ro):
		col = 0
		playerfn = make_play(line, self.cfg, self)
		for column in self.cfg['columns']:
			tmp = no_none_get(line, column, "N/A")
			if tmp != "N/A" and column == "PosterFile":
				image = Image.open(tmp).resize((100, 150), Image.ANTIALIAS)
				photo = ImageTk.PhotoImage(image)
				lb = tk.Label(self.frame, image=photo, height=150, width=100, borderwidth="1", relief="solid",
					anchor=tk.NW, justify=tk.CENTER,
					)
				lb.image = photo
				lb.bind("<Double-Button-1>", playerfn)
			else:
				background = "#BBBBBB"
				if self.searchEntry.get() != "":
					if self.searchEntry.get() in tmp:
						background = "#FFF700"
				width = len(tmp)*10
				if width > 320:
					width = 320
				if len(tmp) > 450:
					tmp = tmp[:450]+"..."
				f = tk.Frame(self.frame, height=150, width=width)
				f.pack_propagate(0)
				lbf = tk.Label(f, text=tmp, borderwidth="1", relief="solid",
					anchor=tk.N, justify=tk.LEFT, wraplength=300,
					bg=background
					)
				lbf.pack(fill=tk.BOTH, expand=1)
				lbf.bind("<Double-Button-1>", playerfn)
				lb = f
			lb.grid(row=ro, column=col, sticky=tk.W+tk.E+tk.N+tk.S)
			col+=1

	def startMove(self, event):
		self.x = event.x
		self.y = event.y

	def stopMove(self, event):
		self.x = None
		self.y = None

	def onMotion(self, event):
		deltax = event.x - self.x
		deltay = event.y - self.y
		self.canvas.yview_scroll(-deltay, "units")
		self.canvas.xview_scroll(-deltax, "units")


	def onFrameConfigure(self, e):
		'''Reset the scroll region to encompass the inner frame'''
		self.canvas.configure(scrollregion=self.canvas.bbox("all"),
				xscrollincrement=1,
				yscrollincrement=1)

	def _on_ymousewheel(self, event):
		self.canvas.yview_scroll(int((event.num-4.5)*30), "units")

	def _on_xmousewheel(self, event):
		self.canvas.xview_scroll(int((event.num-4.5)*30), "units")

	def setupScrollbars(self):
		vsb = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
		self.canvas.configure(yscrollcommand=vsb.set)
		vsb.pack(side="right", fill="y")

		xvsb = tk.Scrollbar(self.root, orient="horizontal", command=self.canvas.xview)
		self.canvas.configure(xscrollcommand=xvsb.set)
		xvsb.pack(side="bottom", fill="x")


def make_play(vid, cfg, self):
	def f(a):
		self.stopMove(None)
		player = getattr(play, cfg['video_player']+'_play')
		player(vid)
	return f

def make_toggle_key(self, column):
	def f(e):
		self.toggleKey(column)
	return f

def getAvailableColumns():
	return Video.getAttrs()

def fromSimpleListStr(sts):
	return trimAll(sts.split(', '))

def trimAll(lis):
	out = []
	for a in lis:
		out.append(a.rstrip().lstrip())
	return out

def toSimpleListStr(cols, sort=False):
	cols = list(cols)
	if sort:
		cols.sort()
	return ', '.join(cols)

def getPlayers():
	opts = dir(play)
	tmp = []
	for a in opts:
		if '_play' in a:
			ind = a.find('_play')
			tmp.append(a[0:ind])
	return tmp

def parseSearch(strs):
	strs = strs.rstrip().lstrip()
	poss = strs.split(' ')
	general = None
	data = {}
	for a in poss:
		if '=' in a:
			col, val = a.split('=',1)
			data[col] = val
		else:
			if general is None:
				general = a
			else:
				general = general + ' ' + a
	return general, data


def no_none_get(a, b, c):
	tmp = a[b]
	if tmp is None:
		return c
	return tmp
