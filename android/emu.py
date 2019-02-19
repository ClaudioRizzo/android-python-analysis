import subprocess
from android.config import Config


class AndroidEmulator():
    def __init__(self, name, proxy='127.0.0.1:8080', sdk_id=''):
        conf = Config()
        self.avdmanager = conf.avdmanager
        self.emulator = conf.emulator
        self.name = name
        self.proxy = proxy
        self.proxy_port = int(self.proxy.split(':')[-1])

        if name not in self.__get_present_avds():  
            try:
                self.__create_avd(name, sdk_id)
            except subprocess.TimeoutExpired:
                raise EmulatorException("Faild to create avd")

    def __get_sdk_id(self):
        proc = subprocess.run(
            [self.avdmanager, 'create', 'avd', '-n', 'foo', '-k', '""'], stderr=subprocess.PIPE)
        stderr = proc.stderr.decode('utf-8')

        # we look for the first instance using an x86 and default API
        for sdk_id in stderr.split('\n'):
            if sdk_id.split(';')[-1] == 'x86' and (sdk_id.split(';')[-2] == "default"):
                return sdk_id

        # Otherwise we return the first we find
        return stderr.split('\n')[1]

    def __get_present_avds(self):
        proc = subprocess.run(
            [self.emulator, '-list-avds'], stdout=subprocess.PIPE)
        stderr = proc.stdout.decode('utf-8')
        return stderr.split('\n')

    def __create_avd(self, name, sdk_id):
        if(sdk_id == ''):
            sdk_id = self.__get_sdk_id()

        proc = subprocess.Popen([self.avdmanager, 'create', 'avd', '-n',
                                 name, '-k', sdk_id], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        proc.communicate(b'no')
        return proc.wait(timeout=20)

    def start_emulator_no_window(self, port):
        '''
        This method starts this emulator listening on the specified port.
        The emulator will be started without a window instance.

        Params:
        port: port where this emulator has to run
        Returns:
        process attached to the started emulator
        '''
        return subprocess.Popen([self.emulator, '-avd', self.name, '-port', str(port),
                                '-no-snapshot-save', '-no-window', '-writable-system'
                                ],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def start_emulator_with_proxy(self, port=5554, 	no_window=True):
        if no_window:
            return subprocess.Popen([self.emulator, '-avd', self.name, '-port', str(port), '-no-snapshot-save', '-no-window', '-writable-system', '-http-proxy', self.proxy],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            return subprocess.Popen([self.emulator, '-avd', self.name, '-port', str(port), '-no-snapshot-save', '-writable-system', '-http-proxy', self.proxy],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class EmulatorException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)