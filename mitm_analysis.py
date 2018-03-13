import subprocess
import time
import os

from queue import Empty
from android.dynamic_analysis import Analysis

EXPLOIT_FOLDER = '/home/clod/BV_ScriptsAndExperiments/RAID_2018/allIfaces'
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


	def do_analysis(self, adb, current_apk, lock, file_lock, clear_process_lock):
		self.log('START', current_apk.apk_id, adb.device)

		exploit_path = os.path.join(EXPLOIT_FOLDER, current_apk.apk_id+'_exploit.js')

		if not os.path.exists(exploit_path):
			self.log('NO_EXPLOIT', current_apk.apk_id, adb.device)
			with open(exploit_path, 'w') as f:
				f.write("console.log('[BabelView] Javascript Executed');")


		bettercap_log = self.open_file_for_log('logs/bettercap_'+str(os.getpid())+'.log', file_lock)
		proxy_process = self.start_proxy_for_analysis(exploit_path, dns_port=str(adb.emulator.proxy_port - 1000), 
			http_port=str(adb.emulator.proxy_port), https_port=str(adb.emulator.proxy_port + 1000), log_file=bettercap_log)
		
		self.add_process(proxy_process.pid, file_lock) # In case of a timeout we are sure this process will be killed
		
		time.sleep(5) # wait for proxy to properly start
		self.log('PROXY', current_apk.apk_id, adb.device)
		
		adb.install_apk(current_apk.path, timeout=60)
		
		self.log('INSTALL', current_apk.apk_id, adb.device)

		clproc = adb.clear_logs()
		logcat = adb.logcat(current_apk.apk_id+'.logcat')
		
		adb.monkey( current_apk.package, timeout=(60*10) )
		
		time.sleep(20)

		self.log('MONKEY', current_apk.apk_id, adb.device)

		adb.stop_logcat(logcat)
		adb.clear_logs()

		adb.uninstall_apk( current_apk.package, timeout=60)
		#self.log('UNINSTALL', current_apk.apk_id, adb.device)
		
		#self.kill(proxy_process.pid)
		proxy_process.kill()
		bettercap_log.close()
		

		adb.reboot_emulator(timeout=60)
		
		self.log('DONE', current_apk.apk_id, adb.device)
		
	
	def log(self, _type, apk_id, dev):
		self.logger.info("[%s] %s (%s -- %s)" % (_type, apk_id, os.getpid(), dev, ))



def main():
	
	mitm = MITMAnalysis(processes=4)
	
	mitm.init_analysis(sdk_id='system-images;android-19;default;x86', no_window=True)
	mitm.init_queues()
	mitm.start_analysis()


	
		

if __name__ == '__main__':
	main()
