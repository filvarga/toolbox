#!/usr/bin/env python2.7
# -*- encoding: utf-8 -*-
# autor: Filip Varga

# content/rootFolder/childEntity/vmFolder/childEntity/childEntity/
# https://www.vmware.com/support/developer/converter-sdk/conv55_apireference/vim.vm.GuestInfo.ToolsStatus.html

# TODO: vytvor casovac aby si vedel kolko priblizne trva kym nabehnu tool
# TODO: vytvor casovac aby si vedel kolko priblizne trva kym nabehne adresa
# TODO: 3) add guest IP & MAC to dhcp server
# TODO: *) add guest to nagios
# TODO: *) RSA KEYS
# TODO: Clone_Task - nema vyznam odstranit - neideme robyt viacero uloh
#       - jedine, ze chces supportovat prerusenie ulohy
#       - stale to mozes cele uzavriet do deploy_vm funkcie

# cucoriedka


from pyVim.connect import SmartConnect, Disconnect
from argparse import ArgumentParser, Action
from sys import exit, stderr, argv
from pyVmomi import vim, vmodl
from time import sleep, time
from atexit import register
from getpass import getpass
from guest import SSHGuest
from config import Config
import logging
import ssl


logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def get_content(username, password, host):
    s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    s.verify_mode = ssl.CERT_NONE
    try:
        service_instance = SmartConnect(
            user=username,
            pwd=password,
            host=host,
            sslContext=s
        )
    except:
        pass
    else:
        register(Disconnect, service_instance)
        return service_instance.RetrieveContent()
    return None


def get_objects(content, type):
    container_view = content.viewManager.CreateContainerView(
        content.rootFolder, [type], True)
    return container_view.view


def get_object(content, type, name):
    for view in get_objects(content, type):
        if view.name == name:
            return view
    return None

def get_first_device(vm, type):
    for device in vm.config.hardware.device:
        if isinstance(device, type):
            return device
    return None


# TODO: yield %
def wait_for_task(task, seconds=1):
    state = task.info.state
    while (state == 'running') or (state == 'queued'):
        sleep(seconds); state = task.info.state
    if state == 'success':
        return True
    return False


def wait_for_tools(v_mor, seconds=60):
    start = time()
    while v_mor.guest.toolsRunningStatus != 'guestToolsRunning':
        sleep(seconds / 10 or 1)
        if (v_mor.guest.toolsStatus == 'toolsNotInstalled') or \
            (time() - start > seconds):
            return False
    return True


def wait_for_ip_address(v_mor, seconds=60):
    start = time()
    address = v_mor.guest.ipAddress
    while not address:
        if (time() - start > seconds):
            break
        sleep(seconds / 10 or 1); address = v_mor.guest.ipAddress
    return address


def clone(
            content,
            template,
            name,
            pool,
            folder,
            datastore,
        ):

    vm_mor = get_object(content, vim.VirtualMachine, template)
    if vm_mor is None:
        logger.error(u'VirtualMachine %s not found' % template)
        return None

    pool_mor = get_object(content, vim.ResourcePool, pool)
    if pool_mor is None:
        logger.error(u'ResourcePoll %s not found' % pool)
        return None

    folder_mor = get_object(content, vim.Folder, folder)
    if folder_mor is None:
        loggeer.error(u'Folder %s not found' % folder)
        return None

    datastore_mor = get_object(content, vim.Datastore, datastore)
    if datastore_mor is None:
        logger.error(u'Datastore %s not found' % datastore)
        return None

    r_spec = vim.VirtualMachineRelocateSpec()
    c_spec = vim.VirtualMachineCloneSpec()

    r_spec.pool = pool_mor
    r_spec.datastore = datastore_mor

    c_spec.location = r_spec
    c_spec.powerOn = True

    # TODO: remake to vm_mor.Clone !!!
    return vm_mor.CloneVM_Task(name=name, folder=folder_mor, spec=c_spec)


def config(
            content,
            name,
            users,
            groups,
            domain,
            username,
            password,
            guest_username,
            guest_password
        ):

    vm_mor = get_object(content, vim.VirtualMachine, name)
    if vm_mor is None:
        logger.error(u'VirtualMachine %s not found' % name)
        return False

    if not wait_for_tools(vm_mor):
        logger.error(u'tools not ready')
        return False

    address = wait_for_ip_address(vm_mor)
    if not address:
        logger.error(u'unable to obtail IP address')
        return False

    logger.info(u'connecting to IP: %s' % address)
    guest = SSHGuest(address, guest_username, guest_password)
    logger.info(u'connected to IP: %s' % address)

    if not guest.upgrade():
        logger.error(u'updating system')
        return False
    
    if not guest.set_hostname(name):
        logger.error(u'changing hostname')
        return False

    if not guest.join(username, password, domain):
        logger.error(u'joining domain')
        return False

    for user in users:
        if not guest.permit_user(user):
            logger.error(u'adding user logon rights')
            return False

    for group in groups:
        if not guest.permit_group(group):
            logger.error(u'adding group logon rights')
            return False

    logger.debug(guest.output)

    return True


def info(content, name):
    vm_mor = get_object(content, vim.VirtualMachine, name)
    if vm_mor is None:
        logger.error(u'VirtualMachine %s not found' % name)
        return False 

    #ethernet = get_first_device(vm_mor, vim.vm.device.VirtualEthernetCard)
    #if ethernet is None:
    #    logger.error(u'no VirtualEthernetCard found')
    #    return False

    #logger.info(u'mac:%s' % ethernet.macAddress)

    for nic in vm_mor.guest.net:
        logger.info(u'mac: %s' % nic.macAddress)
        for ip in nic.ipConfig.ipAddress:
            logger.info(u'ip: %s' % ip.ipAddress)



def setpass(conf, username, attrname):
    if (attrname not in conf) or \
        (not conf.__getattr__(attrname)):

        password = getpass(u'login: %s\n password: ' %
        username)

        if not password:
            logger.error(u'no password entered')
            exit(1)
        
        conf.__setattr__(attrname, password)


def configure(content, conf):
    if conf.guest == 'linux':
        setpass(conf, conf.guest_username, 'guest_password')

        if not config(content,
            conf.name,
            conf.users,
            conf.groups,
            conf.windows_domain,
            conf.windows_username,
            conf.windows_password,
            conf.guest_username,
            conf.guest_password):

            logger.info(u'system not configured')
            exit(1)
    
    logger.info(u'system configured')


def deploy(content, conf):
    if conf.guest == 'linux':
        template = conf.template_linux
    else:
        template = conf.template_windows

    task = None
    try:
        task = clone(content,
            template, conf.name,
            conf.vcenter_pool,
            conf.vcenter_folder,
            conf.vcenter_datastore)
    except KeyboardInterrupt:
        if task and task.info.cancelable:
            task.CancelTask()
    else:
        if task and wait_for_task(task):
            # TODO: logika testovania uspesnosti
            configure(content, conf)
            return
    
    logger.error(u'VirtualMachine not created')
    exit(1)


def add_arguments(subparsers, call):
    parser = subparsers.add_parser(
        call.func_name)
    parser.set_defaults(call=call)

    parser.add_argument('guest', choices=['linux', 'windows'])
    parser.add_argument('name')
    
    parser.add_argument('--vcenter-host', dest='vcenter_host')
    parser.add_argument('--vcenter-pool', dest='vcenter_pool')
    parser.add_argument('--vcenter-folder', dest='vcenter_folder')
    parser.add_argument('--vcenter-datastore', dest='vcenter_datastore')

    parser.add_argument('--windows-domain', dest='windows_domain')
    parser.add_argument('--windows-username', dest='windows_username')
    
    parser.add_argument('--guest-username', dest='guest_username')

    parser.add_argument('--template-linux', dest='template_linux')
    parser.add_argument('--tempalte-windows', dest='template_windows')

    parser.add_argument('--domain-users', dest='users', action='append', default=list())
    parser.add_argument('--domain-groups', dest='groups', action='append', default=list())

    parser.add_argument('-v', '--verbose', default='error', choices=['error', 'debug', 'info'])


def main():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers()

    add_arguments(subparsers, deploy)
    add_arguments(subparsers, configure)

    conf = Config()
    conf.namespace = parser.parse_args()

    logger.setLevel(getattr(logging,
        conf.namespace.verbose.upper()))

    if not conf.read() or not \
        (('vcenter_host' in conf) and \
        ('vcenter_pool' in conf) and \
        ('vcenter_folder' in conf) and \
        ('vcenter_datastore' in conf) and \
        ('windows_domain' in conf) and \
        ('windows_username' in conf) and \
        ('guest_username' in conf)) and \
        ((conf.guest == 'linux') and 
           not ('template_linux' in conf)) or \
        ('template_windows' in conf):
        logger.error("missing configuration parameter")
        exit(1)

    setpass(conf, conf.mail, 'windows_password')

    content = get_content(conf.mail,
        conf.windows_password, conf.vcenter_host)
    
    exit(0)
    if content is None:
        logger.error("connecting to vCenter")
        exit(1)

    conf.call(content, conf)


if __name__ == '__main__':
    main()