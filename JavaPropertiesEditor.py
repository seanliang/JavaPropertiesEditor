# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import os
import re
import sys

if sys.version_info < (3, 0):
	NONE_COMMAND = (None, None, 0)
	MAP = map(unichr, range(0x7f))
else:
	NONE_COMMAND = ('', None, 0)
	MAP = list(map(chr, list(range(0x7f))))

class UpperTable(dict):
	def __missing__(self, key):
		return u'\\u%04X' % key

class LowerTable(dict):
	def __missing__(self, key):
		return u'\\u%04x' % key

UPPER_TABLE = UpperTable(enumerate(MAP))
LOWER_TABLE = LowerTable(enumerate(MAP))
IS_UPPER = re.compile('\\\\u([A-F][A-Z0-9]{3,3}|[0-9][A-F][A-F0-9]{2,2}|[0-9]{2,2}[A-F][A-F0-9]|[0-9]{3,3}[A-F])')

UNIC = '\\u000'
CTRL = '>LRTC<'

class JavaPropertiesConvertCommand(sublime_plugin.TextCommand):
	def run(self, edit, contents):
		view = self.view
		sel = view.sel()
		rs = [x for x in sel]
		vp = view.viewport_position()
		view.set_viewport_position(tuple([0, 0]))
		regions = sublime.Region(0, view.size())
		view.replace(edit, regions, contents)
		sel.clear()
		for x in rs:
			sel.add(sublime.Region(x.a, x.b))
		view.set_viewport_position(vp)
		view.set_scratch(True)
		view.settings().set('set_scratch', True)

class JavaPropertiesEditorListener(sublime_plugin.EventListener):
	def check_properties(self, view):
		file_name = view.file_name()
		result = file_name and file_name.endswith('.properties')
		if result:
			view.settings().set('is_properties', True)
		return result

	def replace_content(self, view, contents):
		view.run_command('java_properties_convert', {'contents': contents})

	def on_load(self, view):
		if not self.check_properties(view):
			return
		regions = sublime.Region(0, view.size())
		orignal_contents = view.substr(regions)
		contents = orignal_contents.replace(UNIC, CTRL).encode('iso-8859-1', 'replace').decode('raw_unicode_escape').replace(CTRL, UNIC)
		if contents == orignal_contents:
			return
		if IS_UPPER.search(orignal_contents) == None:
			view.settings().set('use_lower', True)
		self.replace_content(view, contents)

	def on_modified(self, view):
		if not view.settings().get('is_properties'):
			return
		if view.settings().get('set_scratch'):
			view.settings().erase('set_scratch')
			return
		cmd0 = view.command_history(-1)
		cmd = view.command_history(0)
		if cmd == NONE_COMMAND:
			# no more command, redo it
			view.run_command('redo')
		elif cmd0 == NONE_COMMAND:
			# undo to open
			view.set_scratch(True)
		else:
			view.set_scratch(False)

	def on_pre_save(self, view):
		# check again in case the file was newly created
		if not self.check_properties(view):
			return
		regions = sublime.Region(0, view.size())
		contents = view.substr(regions)
		tab = LOWER_TABLE if view.settings().get('use_lower') else UPPER_TABLE
		orignal_contents = contents.translate(tab)
		if contents == orignal_contents:
			return
		self.contents = contents
		self.replace_content(view, orignal_contents)

	def on_post_save(self, view):
		if not view.settings().get('is_properties'):
			return
		if not hasattr(self, 'contents'):
			return
		contents = self.contents
		del self.contents
		self.replace_content(view, contents)
