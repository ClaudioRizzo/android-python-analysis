import subprocess
import time
import logging
import os

from android import emu, adb_wrapper, apk
from android import config

from multiprocessing import Queue, Process, Lock, Manager, Value
from multiprocessing.pool import Pool
from queue import Empty

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
		self.proxy_ip = conf.proxy
		self.name = name
		self.processes = processes
		self.apk_queue = Queue()
		self.adb_queue = Queue()
		m = Manager()
		self.busy_pid = m.dict()
		self.emulators = [] # a list containing all the started emulators process
		self.adbs = [] # list of all the running adb wrappers

		self.hard_restart = Value('i', 0)
		self.__process_to_clear = m.list()
		self.__log_files = m.list()
		self.__no_window = True

		

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

	def init_analysis(self, emu_name='DynamicAnalysis', sdk_id='', no_window=True):
		proxy_port = 8080
		emu_port = 5554
		self.__no_window = no_window
		
		for i in range(self.processes):
			
			name = emu_name+'_'+str(i)
			proxy_port += i
			proxy = self.proxy_ip+':'+str(proxy_port)
			
			a_emu = emu.AndroidEmulator(name, proxy=proxy, sdk_id=sdk_id)
			emu_proc = a_emu.start_emulator_with_proxy(port=emu_port, no_window=self.__no_window)
			self.emulators.append(emu_proc)

			dev = 'emulator-'+str(emu_port)
			adb = adb_wrapper.ADB(dev, emulator=a_emu)
			emu_port+=2

			self.adbs.append(adb)
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

	'''
	This method will be called when an hard restart is needed, for example if adb gets stuck for some emulator
	'''
	def __hard_analysis_restart(self, device, no_window=True):
		#for p in self.emulators:
			#p.kill()
			##subprocess.run(['kill', '-9', str(p.pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		#p = subprocess.run(['killall', 'emulator64-crash-service'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		for adb in self.adbs:
			self.__kill_one_to_kill_all(adb.dev_port, adb.emulator.name)

		del self.emulators[:]

		self.log("HARD_RESTART", "killing adb server" , device)
		adb_wrapper.kill_server()

		self.log("HARD_RESTART", "restarting adb server" , device)
		adb_wrapper.start_server()

		for adb in self.adbs:
			self.log("HARD_RESTART", "restarting emulator" , adb.device)
				
			emu_proc = adb.emulator.start_emulator_with_proxy(port=adb.dev_port, no_window=no_window)
			
			self.emulators.append(emu_proc)

		self.log("HARD_RESTART", "restarting called by %s completed" % device , device)


	def start_analysis(self):
		
		workers = MyPool(self.processes, self.__analysis, (Lock(), Lock(), Lock(), ) )
		workers.close()
		workers.join()

		self.__kill_to_clear()
		#self.__close_all_pending_files()

	def __analysis(self, lock, file_lock, clear_process_lock):
			
		adb = self.__get_adb_from_queue()
		
		#self.__wait_for_device(adb, timeout=60)


		while not self.apk_queue.empty():
			try:
				lock.acquire()
				with self.hard_restart.get_lock():
					if self.hard_restart.value == 1:
						self.__wait_for_other_processes()
						self.__hard_analysis_restart(adb.device, no_window=self.__no_window)
						self.hard_restart.value = 0 
						self.__kill_to_clear()
						#self.__close_all_pending_files()
				lock.release()

				self.busy_pid[os.getpid()] = os.getpid()
				
				adb.wait_for_device(timeout=60)
				self.__wait_for_boot(adb, timeout=60)
				
				current_apk = self.apk_queue.get(True, 10)
				self.do_analysis(adb, current_apk, lock, file_lock, clear_process_lock)

				self.busy_pid.pop(os.getpid(), None)

			except Empty as e1:
				self.log('INFO', 'The queue was empty', adb.device)
				self.logger.error("(%s) %s" % (adb.device, e1, ))
				self.busy_pid.pop(os.getpid(), None)

			except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception) as e:
				self.log('GENERAL_ERROR', 'A timeout or an error happened: %s' % current_apk.apk_id, adb.device)
				self.logger.error("(%s) %s" % (adb.device, e, ))

				self.busy_pid.pop(os.getpid(), None)
				
				with self.hard_restart.get_lock():
					self.hard_restart.value = 1


		

		
		adb.stop_emulator()
		self.log('INFO', 'Analysis completed', adb.device)





	def do_analysis(self):
		raise NotImplementedError

	def log(self, _type, message, emulator):
		self.logger.info("[%s] %s (%s -- %s)" % (_type, message, os.getpid(), emulator, ))		

	def add_process(self, process, l):
		l.acquire()
		self.__process_to_clear.append(process)
		l.release()

	def __kill_to_clear(self):
		
		for p in self.__process_to_clear:
			subprocess.call(['kill', str(p)])
		del self.__process_to_clear[:]
		

	def __wait_for_other_processes(self):
		# Until there is some process busy
		while self.busy_pid:
			# wait for the process to be free
			time.sleep(1)
			print("waiting for something: "+str(self.busy_pid))

	def __get_adb_from_queue(self):
		try:		
			adb = self.adb_queue.get(True, 10)
			return adb
		except Empty:
			self.log('SEVERE', "Process killed due to empty adb queue", "")
			return

	def __wait_for_boot(self, adb, timeout=60):
		self.log('BOOT', "waiting for device to boot", adb.device)
		adb.wait_for_boot(timeout)

	def __close_all_pending_files(self):
		for fd in self.__log_files:
			os.close(fd)
		del self.__log_files[:]

	def open_file_for_log(self, path, lock):
		f = open(path, 'a')
		lock.acquire()
		self.__log_files.append(f.fileno())
		lock.release()
		return f

	def __kill_one_to_kill_all(self, port, avd_name):
		cmd = ['pgrep', '-f', 'port %s' % port]
		p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)		
		stdout = p.stdout.decode('utf-8').strip()
		subprocess.run(['kill', '-9', stdout ] )
		subprocess.run(['killall', 'emulator64-crash-service'])
		subprocess.run(['rm', '-f', os.path.expanduser('~')+'/.android/avd/'+avd_name+'.avd/hardware-qemu.ini.lock'])



