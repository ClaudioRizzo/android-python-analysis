import subprocess
import time
import os

from queue import Empty
from android.dynamic_analysis import Analysis

EXPLOIT_FOLDER = '/home/clod/run_babelview/interfaces'
#EXPLOIT_FOLDER = '/home/clod/workspace/BabelView/interfaces'

class MITMAnalysis(Analysis):
	def __init__(self, processes=1,  name='AndroidAnalysis'):
		super().__init__(processes, name)
		


	def start_proxy_for_analysis(self, exploit_path, dns_port='5300', http_port='8080', https_port='8083', log_file='bettercap.log'):
		proc =  subprocess.Popen( ['bettercap', '-T', '127.0.0.1','--dns-port', dns_port, '--proxy-port', http_port, '--proxy-https-port', 
								   https_port, '--proxy-module', 'injectjs', '--js-file', exploit_path], stdout=log_file, stderr=log_file )

		return proc

	def sudo_kill(self, pid):
		subprocess.call(['sudo', 'pkill','-TERM','-P', str(pid)])

	def kill(self, pid):
		subprocess.call(['kill', str(pid)])

	def analysis(self):
		
		adb_log = open('logs/adb_'+str(os.getpid())+'.log', 'a')
		monkey_log = open('logs/monkey_'+str(os.getpid())+'.log', 'a')
		bettercap_log = open('logs/bettercap_'+str(os.getpid())+'.log', 'a')
		
		
		try:		
			adb = self.adb_queue.get(True, 10)
		except Empty:
			self.log('SEVERE', "Process killed due to empty adb queue", "")
			return
		
		dev = adb.device
		state = adb.get_state()
		
		self.log('INFO', "waiting for device...", dev)
		while state != 'device\n':
			time.sleep(1)
			state=adb.get_state()
		

		self.log(os.getpid(), "Analysis started...", dev)
		current_apk = None
		while not self.apk_queue.empty():
			try:
				state = adb.get_state()
				
				while state != 'device\n':
					time.sleep(1)
					state=adb.get_state()
				
				if current_apk is None:
					current_apk = self.apk_queue.get(True, 10)
					self.log('FETCH', current_apk.apk_id, dev)
				

				exploit_path = os.path.join(EXPLOIT_FOLDER, current_apk.apk_id+'_exploit.js')
				
				if not os.path.exists(exploit_path):
					self.log('NO_EXPLOIT', current_apk.apk_id, dev)
					self.log('DONE', current_apk.apk_id, dev)
					current_apk = None
				else:
					proxy_process = self.start_proxy_for_analysis(exploit_path, dns_port=str(adb.emulator.proxy_port - 1000), 
						http_port=str(adb.emulator.proxy_port), https_port=str(adb.emulator.proxy_port + 1000), log_file=bettercap_log)
					time.sleep(5) # wait for proxy to properly start
					self.log('PROXY', current_apk.apk_id, dev)
					
					try:
						iproc = adb.install_apk(current_apk.path, timeout=60)
						adb_log.write(iproc.stdout.decode('utf-8'))
						
						self.log('INSTALL', current_apk.apk_id, dev)
						
						clproc = adb.clear_logs()
						adb_log.write(clproc.stdout.decode('utf-8'))
						
						logcat = adb.logcat(current_apk.apk_id+'.logcat')
						
						mproc = adb.monkey( current_apk.package, timeout=(60*10))
						monkey_log.write(mproc.stdout.decode('utf-8'))
						time.sleep(20) # wait for a possible request to be finished... 
						self.log('MONKEY', current_apk.apk_id, dev)

						adb.stop_logcat(logcat)
						

						clproc = adb.clear_logs()
						adb_log.write(clproc.stdout.decode('utf-8'))
						
						uproc = adb.uninstall_apk( current_apk.package, timeout=60)
						adb_log.write(uproc.stdout.decode('utf-8'))
						
						self.kill(proxy_process.pid)
						self.log('DONE', current_apk.apk_id, dev)
						current_apk = None
					except subprocess.TimeoutExpired:
						adb.stop_emulator()
						adb.emulator.start_emulator_with_proxy(port=adb.dev_port, no_window=False)
						self.log('RE_LAUNCH', current_apk.apk_id, dev)

			except Empty:
				self.log('INFO', 'The queue was empty', dev)
			
			try:
				adb.reboot_emulator(timeout=20)
			except subprocess.TimeoutExpired:
				adb.stop_emulator()
				adb.emulator.start_emulator_with_proxy(port=adb.dev_port, no_window=False)
				self.log('RE_LAUNCH', os.getpid(), dev)
		
		self.log('ANALYSIS_COMPLETED', os.getpid(), dev)
		adb.stop_emulator()
		
		adb_log.close()
		monkey_log.close()
		bettercap_log.close()
		

		
	def log(self, _type, apk_id, dev):
		self.logger.info("[%s] %s (%s -- %s)" % (_type, apk_id, os.getpid(), dev, ))



def main():
	
	mitm = MITMAnalysis(processes=4)
	
	mitm.init_analysis(sdk_id='system-images;android-19;default;x86', no_window=False)
	mitm.init_queues()
	mitm.do_analysis()


	
		

if __name__ == '__main__':
	main()
