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
from argparse import ArgumentParser
from pyVmomi import vim, vmodl
from time import sleep, time
from atexit import register
from getpass import getpass
from guest import SSHGuest
from config import Config
from sys import stdout
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
        stdout.write('\rProgress: %s %%' % task.info.progress)
        stdout.flush()
        sleep(seconds); state = task.info.state
    if state == 'success':
        print('\rProgress: 100 %')
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


def setpass(conf, username, attrname):
    if (attrname not in conf) or \
        not getattr(conf, attrname):

        password = getpass(u'login: %s\n password: ' %
        username)

        if not password:
            logger.error(u'no password entered')
            exit(1)
        
        setattr(con, attrname, password)


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

        status = (task is not None) and \
            wait_for_task(task)
    except KeyboardInterrupt:
        if (task is not None) and task.info.cancelable:
            # CancelTask() returns None
            task.CancelTask()
            loogger.error(u'Clone Task canceled')
    else:
        if status:
            # TODO: logika testovania uspesnosti
            #configure(content, conf)
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
    parser.add_argument('--template-windows', dest='template_windows')

    parser.add_argument('--domain-users', dest='users', action='append', default=list())
    parser.add_argument('--domain-groups', dest='groups', action='append', default=list())

    parser.add_argument('-v', '--verbosity', default='error', choices=['error', 'debug', 'info'])


def main():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers()
    
    add_arguments(subparsers, deploy)
    add_arguments(subparsers, configure)

    args = parser.parse_args()

    conf = Config(namespace=args)

    if not conf.read():
        logger.error("missing config file")
        exit(1)

    required = [
        'vcenter_host',
        'vcenter_pool',
        'vcenter_folder',
        'guest_username',
        'windows_domain',
        'windows_username',
        'vcenter_datastore'
        ]

    if args.guest == 'linux':
        required.append('template_linux')
    else:
        required.append('template_windows')

    for attrname in required:
        if ((not attrname in conf) or 
            (not getattr(conf, attrname))):

            logger.error("missing attribute {}".format(
                attrname))
            exit(1)

    setpass(conf, conf.mail, 'windows_password')

def _():
    content = get_content(conf.mail,
        conf.windows_password, conf.vcenter_host)

    if not content:
        logger.error("connecting to vCenter")
        exit(1)
    
    conf.call(content, conf)


if __name__ == '__main__':
    main()