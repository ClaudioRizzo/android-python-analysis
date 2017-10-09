import subprocess

class APK():
	def __init__(self, apk_path, aapt_path='aapt'):
		self.aapt = aapt_path
		self.path = apk_path
		self.package = None


	def get_package_name(self):
	    
	    if self.package is None:
		    proc = subprocess.run(['aapt', 'dump', 'badging', self.path], stdout=subprocess.PIPE)
		    out = proc.stdout.decode('utf-8')
		    
		    m = re.search(r'package: name.*', out)
		    if m:
		        line = m.group(0)
		        self.package = line.split(' ')[1].split('=')[1].replace("'", "").replace('\n', '')
		
		return self.package

