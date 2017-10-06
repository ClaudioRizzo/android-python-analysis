import subprocess
import os

class ADB():

	'''
	@param: device - the name of the device this ADB has to manage
	@param: adb_path - path to adb executable in the SDK. By default it is assumed to be in the PATH variable
	'''
	def __init__(self, device, adb_path='adb'):
		self.device = device
		self.adb = adb_path
		self.dir_path = os.path.dirname(os.path.realpath(__file__))

	def start_server(self):
		return subprocess.run([self.adb, 'start_server'], stdout=subprocess.PIPE)
		
		
	def get_state(self):
		return subprocess.run(['adb', '-s', self.device, 'get-state'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	def install_apk(self, apk_path):
		return subprocess.run(['adb', '-s', self.device, 'install', apk_path])

	def uninstall_apk(self, apk_package):
		return subprocess.run(['adb', '-s', self.device, 'uninstall', apk_package])

	def monkey(self, package_name):
		return subprocess.run(['adb', '-s', self.device, 'shell', 'monkey', '-p', package_name, '--throttle', '2000', '100'])

	def logcat(self, file_name=None):
		logcat_file = None
		
		if file_name is None:
			logcat_process = subprocess.Popen([self.adb, '-s', self.device, 'logcat'])
		else:
			logcat_file = open(os.path.join(self.dir_path, file_name), 'w')
			logcat_process = subprocess.Popen([self.adb, '-s', self.device, 'logcat'], stdout=logcat_file)
		
		return (logcat_file, logcat_process)

	def stop_logcat(self, logcat):
		logcat.pid.terminate()
		logcat.log_file.close()

	def force_logcat_stop(self, logcat_pid):
		logcat.pid.kill()
		logcat.log_file.close()

	def clear_logs(self):
		subprocess.run([self.adb, '-s', self.device, 'logcat', '-c'])

class LogCat():
	def __init__(self, log_file, pid):
		self.log_file = log_file
		self.pid = pid
