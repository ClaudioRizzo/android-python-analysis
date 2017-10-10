import subprocess
import time
import logging
import os

from android import emu, adb_wrapper, apk
from android import config

from multiprocessing import Queue, Process
from multiprocessing.pool import Pool

class NoDaemonProcess(Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)


class MyPool(Pool):
    def __reduce__(self):
        super(MyPool, self).__reduce__()

    Process = NoDaemonProcess

class NoDeviceFoundError(Exception):
	pass

class Analysis():

	def __init__(self, processes=1,  name='AndroidAnalysis'):
		conf = config.Config()
		self.id_file = conf.ids
		self.logger = self.__set_logger(name, log_file=name+'.log', log_file_mode='a')
		self.apk_folder = conf.apks
		self.name = name
		self.processes = processes
		self.apk_queue = Queue()
		self.adb_queue = Queue()
		

	def __get_devices(self):
		proc = subprocess.run(['adb', 'devices'], stdout=subprocess.PIPE)
		out = proc.stdout.decode('utf-8')
		devices = [dev.split("	")[0].replace(' ','').replace('\n', '') for dev in out.split('\n')[1:] if dev != '' ] 
		return devices

	def __set_logger(self, name, log_file=None, log_file_mode='w'):
	    lg = logging.getLogger(name)
	    lg.setLevel(logging.DEBUG)
	    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
	    ch = logging.StreamHandler()
	    ch.setFormatter(formatter)
	    lg.addHandler(ch)
	    if log_file is not None:
	        fh = logging.FileHandler(log_file, log_file_mode)
	        fh.setFormatter(formatter)
	        lg.addHandler(fh)
	    return lg

	def init_analysis(self, emu_name='DynamicAnalysis', sdk_id=''):
		proxy_port = 8080
		emu_port = 5554
		
		for i in range(self.processes):
			
			name = emu_name+'_'+str(i)
			proxy_port += i
			proxy = '134.219.188.141:'+str(proxy_port)
			
			a_emu = emu.AndroidEmulator(name, proxy=proxy, sdk_id=sdk_id)
			a_emu.start_emulator_with_proxy(port=emu_port, no_window=False)
			dev = 'emulator-'+str(emu_port)
			print(dev)
			adb = adb_wrapper.ADB(dev, emulator=a_emu)
			emu_port+=2

			self.adb_queue.put(adb)

		# if the processes are more than the abds
		# then there was an error in starting the emulators
		if self.adb_queue.qsize() != self.processes:
			raise RuntimeError


	def init_queues(self):
		with open(self.id_file, 'r') as apks_file:
			apks = apks_file.readlines()

		for apk_id in apks:
			apk_id = apk_id.replace('\n', '')
			apk_path = os.path.join(self.apk_folder, apk_id+'.apk')
			
			_apk = apk.APK(apk_path)
			self.apk_queue.put(_apk)


	def do_analysis(self):
		workers = MyPool(self.processes, self.analysis, )
		workers.close()
		workers.join()

	def analysis(self):
		raise NotImplementedError

