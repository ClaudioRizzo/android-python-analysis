import subprocess
import os

from android.config import Config

def start_server():
	c = Config()
	return subprocess.run([c.adb, 'start-server'], stdout=subprocess.PIPE)

def kill_server():
	c = Config()
	return subprocess.run([c.adb, 'kill-server'], stdout=subprocess.PIPE)


class ADB():

	'''
	@param: device - the name of the device this ADB has to manage
	@param: adb_path - path to adb executable in the SDK. By default it is assumed to be in the PATH variable
	'''
	def __init__(self, device, emulator):
		conf = Config()
		self.device = device
		self.dev_port = int(device.split('-')[-1])
		self.emulator = emulator
		self.adb = conf.adb
		self.results = conf.results
		self.dir_path = os.path.dirname(os.path.realpath(__file__))
		self.log_file_out = 'logs/adb_out_'+str(os.getpid())+'.log'
		self.log_file_err = 'logs/adb_err_'+str(os.getpid())+'.log'

	def get_state(self):
		proc = subprocess.run(['adb', '-s', self.device, 'get-state'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		return proc.stdout.decode('utf-8')
	
	def install_apk(self, apk_path, timeout=None):
		proc =  subprocess.run(['adb', '-s', self.device, 'install', apk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
		self.__log(proc)
		return proc
	
	def uninstall_apk(self, apk_package, timeout=None):
		proc = subprocess.run(['adb', '-s', self.device, 'uninstall', apk_package], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
		self.__log(proc)
		return proc
	
	def monkey(self, package_name, timeout=None):
		proc = subprocess.run(['adb', '-s', self.device, 'shell', 'monkey', '-p', package_name, '--throttle', '2000', '100'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
			timeout=timeout)
		self.__log(proc)
		return proc

	def logcat(self, file_name=None):
		logcat_file = None
		
		if file_name is None:
			logcat_process = subprocess.Popen([self.adb, '-s', self.device, 'logcat'])
		else:
			logcat_file = open(os.path.join(self.results, file_name), 'w')
			logcat_process = subprocess.Popen([self.adb, '-s', self.device, 'logcat'], stdout=logcat_file)
		
		return LogCat(logcat_file, logcat_process)

	def stop_logcat(self, logcat):
		logcat.log_file.close()
		logcat.pid.terminate()
		

	def force_logcat_stop(self, logcat_pid):
		logcat.pid.kill()
		logcat.log_file.close()

	def clear_logs(self):
		return subprocess.run([self.adb, '-s', self.device, 'logcat', '-c'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


	def push_file_to_emu(self, origin, destination):
		subprocess.run([self.adb, '-s', self.device, 'push', origin, destination], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	def __writable_sdcard(self):
		subprocess.run([self.adb, '-s', self.device, 'shell','su','-c', '"mount -o rw,remount rootfs /"'])
		subprocess.run([self.adb, '-s', self.device, 'shell', '"chmod 777 /mnt/sdcard"'])

	def setup_ca(self, cacert_path, cacert_name):
		#subprocess.run([self.adb, '-s', self.device, 'root'])
		subprocess.run([self.adb, '-s', self.device, 'shell', 'su','-c', '"mount -o remount,rw /system"'])
		#print (" ".join([self.adb, '-s', self.device, 'shell', 'su','-c', '"mount -o remount,rw /system"']))
		self.push_file_to_emu(cacert_path, '/system/etc/security/cacerts/')
		subprocess.run([self.adb, '-s', self.device, 'shell', 'su','-c', '"chmod 644 /system/etc/security/cacerts/'+cacert_name+'"'])
		subprocess.run([self.adb, '-s', self.device, 'shell', 'reboot'])

	def stop_emulator(self):
		return subprocess.run([self.adb, '-s', self.device, 'emu', 'kill'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	def reboot_emulator(self, timeout=None):
		return subprocess.run([self.adb, '-s', self.device, 'reboot'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)

	def __log(self, p):
		stdout = p.stdout.decode('utf-8')
		stderr = p.stderr.decode('utf-8')

		with open(self.log_file_out, 'a') as o:
			o.write(stdout)

		with open(self.log_file_err) as e:
			e.write(stderr)


class LogCat():
	def __init__(self, log_file, pid):
		self.log_file = log_file
		self.pid = pid
