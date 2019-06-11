from crl.interactivesessions.shells.sshshell import SshShell
from crl.interactivesessions.shells.registershell import RegisterShell

@RegisterShell()
class KeyAuthenticatedShell(SshShell):


    _ssh_options = (" -o 'UserKnownHostsFile=/dev/null'"
                    " -o 'ServerAliveInterval=15'"
                    " -o 'StrictHostKeyChecking=no'"
                    " -o 'PasswordAuthentication=no'"
                    " -o ConnectTimeout=30")
     
    def get_start_cmd(self):
        return ("ssh {0} {1}".format(self._ssh_options, self.ip)
                if self.username is None else
                "ssh {0} {1}@{2}".format(self._ssh_options, self.username, self.ip))


