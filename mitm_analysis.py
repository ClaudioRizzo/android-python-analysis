import subprocess
import time
import os

from android.dynamic_analysis import Analysis

EXPLOIT_FOLDER = '/home/clod/workspace/BabelView/interfaces'

class MITMAnalysis(Analysis):
	def __init__(self, processes=1,  name='AndroidAnalysis'):
		super().__init__(processes, name)


	def start_proxy_for_analysis(self, exploit_path, dns_port='5300', http_port='8080', https_port='8083'):
		return subprocess.Popen( ['sudo', 'bettercap', '-T', '127.0.0.1','--dns-port', dns_port, '--proxy-port', http_port, '--proxy-https-port', 
								   https_port, '--proxy-module', 'injectjs', '--js-file', exploit_path] )

	def sudo_kill(self, pid):
		subprocess.call(['sudo', 'pkill','-TERM','-P', str(pid)])

	def analysis(self):
		print("Analysis started...")
		adb = self.adb_queue.get(False)

		state = adb.get_state()
		while state != 'device\n':
			time.sleep(1)
			state=adb.get_state()
			self.log('INFO', "waiting for device")


		while not self.apk_queue.empty():
			current_apk = self.apk_queue.get(False)
			
			self.log('FETCH', current_apk.apk_id)
			
			exploit_path = os.path.join(EXPLOIT_FOLDER, current_apk.apk_id+'_exploit.js')
			
			if not os.path.exists(exploit_path):
				self.log('NO_EXPLOIT', current_apk.apk_id)
				continue

			proxy_process = self.start_proxy_for_analysis(exploit_path, dns_port=str(adb.emulator.proxy_port - 1000), 
				http_port=str(adb.emulator.proxy_port), https_port=str(adb.emulator.proxy_port + 1000))
			time.sleep(5) # wait for proxy to properly start
			self.log('PROXY', current_apk.apk_id)
			
			adb.install_apk(current_apk.path)
			self.log('INSTALL', current_apk.apk_id)
			
			adb.clear_logs()
			logcat = adb.logcat(current_apk.apk_id+'.logcat')
			
			adb.monkey( current_apk.package )
			time.sleep(20) # wait for a possible request to be finished... 
			self.log('MONKEY', current_apk.apk_id)

			adb.stop_logcat(logcat)
			adb.clear_logs()
			adb.uninstall_apk( current_apk.package )
			self.sudo_kill(proxy_process.pid)
			self.log('DONE', current_apk.apk_id)
		
	def log(self, _type, apk_id):
		self.logger.info("[%s] %s" % (_type, apk_id,))



def main():
	mitm = MITMAnalysis(processes=2)
	
	mitm.init_analysis(sdk_id='system-images;android-19;default;x86')
	mitm.init_queues()
	mitm.do_analysis()

if __name__ == '__main__':
	main()
