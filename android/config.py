import json

class Config():
	class __Config:
		def __init__(self):
			with open('android/config.json', 'r') as j_file:
				j_data = json.load(j_file)

				self.adb = j_data['adb']
				self.aapt = j_data['aapt']
				self.emulator = j_data['emulator']
				self.avdmanager = j_data['avdmanager']
				self.apks = j_data['apks']
				self.ids = j_data['ids']
				self.results = j_data['results']
				self.proxy = j_data['proxy']

	__instance = None
	def __init__(self):
		if Config.__instance is None:
			# Create and remember instance
			Config.__instance = Config.__Config()

	def __getattr__(self, attr):
		""" Delegate access to implementation """
		return getattr(self.__instance, attr)

	def __setattr__(self, attr, value):
		""" Delegate access to implementation """
		return setattr(self.__instance, attr, value)