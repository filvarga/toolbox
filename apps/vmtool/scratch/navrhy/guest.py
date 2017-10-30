#!/usr/bin/env python2.7
# -*- encoding: utf-8 -*-
# autor: Bc. Filip Varga

from paramiko import SSHClient,\
    AutoAddPolicy
from atexit import register
from select import select
import marshal
import pickle
import base64

RETURN = '\n'


class SSHConnector(object):

    debug = False
    timeout = 30.0

    def __init__(self, hostname, username, password):
        self.password = password
        self.username = username
        self.hostname = hostname

        self.output = str()

        self.connect()

    def connect(self):
        self.client = SSHClient()
        self.client.set_missing_host_key_policy(
            AutoAddPolicy())
        
        try:
            self.client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password)

        except:
            raise Exception('paramiko connection error')
        
        self.channel = self.client.invoke_shell()
        self.channel.settimeout(self.timeout)

        register(self.close)

    def close(self):
        self.channel.close()
        self.client.close()

    def _write(self, command):
        if self.debug:
            self.output += command + RETURN

        _, out, err = \
            self.client.exec_command(command)
        
        while not out.channel.exit_status_ready():
            if out.channel.recv_ready():
                rl, _, _ = select([out.channel], [], [], self.timeout)
                if len(rl) > 0:
                    self.output += out.channel.recv(1024)

        return out.channel.recv_exit_status()

    def run(self, command, elevate=False):
        return self._write(
            '{}/bin/bash -c "({}) 2>&1 || exit 1"'.format(
               'sudo ' if elevate else '', command)) == 0

    def call(self, callback, args=list(), kwargs=dict(), elevate=False):
        return self._write(
            '{}/usr/bin/python -c "import base64,pickle,marshal,types;'\
            'types.FunctionType(marshal.loads(base64.b64decode(\'{}\')),'\
            'globals())(*pickle.loads(base64.b64decode(\'{}\')),'\
            '**pickle.loads(base64.b64decode(\'{}\')))" 2>&1'.format(
            'sudo ' if elevate else '',
            base64.b64encode(marshal.dumps(callback.func_code)),
            base64.b64encode(pickle.dumps(args)),
            base64.b64encode(pickle.dumps(kwargs)))) == 0


class SSHGuest(SSHConnector):

    # TODO: vyuzi netaddr.IPAddress triedu
    def set_interface(self, address, netmask, gateway, nameservers):
        def callback(value1, value2, value3, value4):
            import os
            exit(os.system(
                'printf "'\
                'auto eth0\n'\
                'iface eth0 inet static\n'\
                '\taddress {}\n'\
                '\tnetmask {}\n'\
                '\tgateway {}\n'\
                '\tdns-nameservers {}\n"'\
                ' > /etc/network/interfaces.d/eth0'.format(
                    value1, value2, value3, value4)))
        return self.call(callback,
            [address, netmask, gateway, nameservers],
            elevate=True)

    def set_hostname(self, hostname):
        def callback(value):
            import os
            exit(os.system(
                '(hostnamectl set-hostname {0})&&'\
                '(sed -i "/^127.0.1.1/c\\127.0.1.1\t{0}" /etc/hosts)'.format(
                    value)))
        return self.call(callback, [hostname], elevate=True)

    def upgrade(self):
        def callback():
            import os
            exit(os.system(
                '(export DEBIAN_FRONTEND=noninteractive)&&'\
                '(apt-get update)&&(apt-get upgrade -y)||(exit 1)'))
        return self.call(callback, elevate=True)

    def leave(self):
        def callback():
            import os
            exit(os.system('(realm leave)||(exit 1)'))
        return self.call(callback, elevate=True)

    def join(self, username, password, domain):
        def callback1(value1, value2):
            import subprocess
            p = subprocess.Popen(
                ['/usr/bin/kinit', '-c', 'FILE:/tmp/krb5cc_0', value1],
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE)
            p.communicate(value2)
            exit(p.returncode)
        #def callback2():
        def callback2(value):
            import os
            #exit(os.system('(realm join)||(exit 1)'))
            # TODO: realm nevracia return code
            exit(os.system('(realm join {})||(exit 1)'.format(value)))
        return self.call(callback1, [username, password]) and \
            self.call(callback2, [domain], elevate=True)
    
    def permit_group(self, group):
        def callback(value):
            import os
            exit(os.system('(realm permit -g {})||(exit 1)'.format(value)))
        return self.call(callback, [group], elevate=True)

    def permit_user(self, user):
        def callback(value):
            import os
            exit(os.system('(realm permit {})||(exit 1)'))
        return self.call(callback, [user], elevate=True)
