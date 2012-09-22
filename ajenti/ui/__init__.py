import random
import gevent

from ajenti.api import *


class UIProperty (object):
	def __init__(self, name, value):
		self.dirty = False
		self.name = name
		self.value = value

	def get(self):
		return self.value

	def set(self, value):
		self.dirty = self.value != value
		self.value = value


@interface
class UIElement (object):
	id = None
	__last_id = 0

	@classmethod
	def __generate_id(cls):
		cls.__last_id += 1
		return cls.__last_id

	def __init__(self, ui, id=None, **kwargs):
		self.ui = ui

		if id is not None:
			self.id = id
		
		self._ = UIElement.__generate_id()

		if not hasattr(self, '_properties'):
			self._properties = []
		
		self.children = []
		
		self.properties = {}
		for prop in self._properties:
			self.properties[prop.name] = prop
		for key in kwargs:
			self.properties[key].set(kwargs[key])
		
		self.events = {}
		self.init()

	def init(self):
		pass

	def find(self, _):
		if self._ == _:
			return self
		for child in self.children:
			found = child.find(_)
			if found:
				return found

	def render(self):
		result = {
			'_': self._,
			'id': self.id,
			'events': self.events.keys(),
			'children': [c.render() for c in self.children],
		}
		for prop in self.properties.values():
			result[prop.name] = prop.value
		return result

	def on(self, event, handler):
		self.events[event] = handler

	def publish(self):
		self.ui.queue_update()

	def event(self, event, params=None):
		if event in self.events:
			self.events[event](**(params or {}))

	def append(self, child):
		self.children.append(child)

	def remove(self, child):
		self.children.remove(child)


class UI (object):
	def __init__(self):
		self.pending_updates = 0
		self.on_new_updates = lambda x: None

	@staticmethod
	def create(id, *args, **kwargs):
		for cls in UIElement.get_classes():
			if cls.id == id:
				return cls(*args, **kwargs)
		return UIElement(id=id, *args, **kwargs)

	def render(self):
		return self.root.render()

	def find(self, _):
		return self.root.find(_)

	def dispatch_event(self, _, event, params=None):
		self.find(_).event(event, params)

	def queue_update(self):
		self.pending_updates += 1
		gevent.spawn(self.__worker)

	def send_updates(self):
		self.on_new_updates()
		self.pending_updates = 0

	def __worker(self):
		update_count = self.pending_updates
		gevent.sleep(0.2)
		if update_count == self.pending_updates: # No new updates
			self.send_updates()


def p(prop, default=None):
	def decorator(cls):
		prop_obj = UIProperty(prop, value=default)
		if not hasattr(cls, '_properties'):
			cls._properties = []
		cls._properties.append(prop_obj)

		def get(self):
			return self.properties[prop].get()

		def set(self, value):
			return self.properties[prop].set(value)

		setattr(cls, prop, property(get, set))
		return cls
	return decorator


__all__ = ['UI', 'UIElement', 'p']