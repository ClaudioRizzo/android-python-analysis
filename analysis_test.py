import subprocess
import time
import os

from queue import Empty
from android.dynamic_analysis import Analysis

class MyAnalysis(Analysis):

	

	def do_analysis(self, adb, current_apk, lock):

		self.kill_one_to_kill_all(adb.dev_port)
		time.sleep(5)
		adb.emulator.start_emulator_with_proxy(port=adb.dev_port, no_window=False)
		print("zzzZZZzzZZ")
		time.sleep(100)




def testing(p):
	stdout, stderr = p.communicate()
	print (stdout)
	#print(stderr)
	print("\n\n\n\n\n")


def main():
	
	mitm = MyAnalysis(processes=1)
	
	mitm.init_analysis(sdk_id='system-images;android-19;default;x86', no_window=False)
	mitm.init_queues()
	mitm.start_analysis()

if __name__ == '__main__':
	main()