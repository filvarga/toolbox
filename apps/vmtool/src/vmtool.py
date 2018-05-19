#!/usr/bin/env python2.7
# -*- encoding: utf-8 -*-
# autor: Filip Varga

from argparse import ArgumentParser
from ConfigParser import SafeConfigParser, \
    NoOptionError
from vmware import clone, vim \
    get_object, wait_for_task, \
    wait_for_tools, wait_for_ip_address
from guest import SSHGuest
from sys import stderr


def test_args(args, required):

    for attrname in required:
        if ((not attrname in args) or
            (getattr(conf, attrname) is None)):

            stderr.write(u"Error: missing attribute {}".format(attrname))
            exit(1)


def deploy(content, args):

    test_args(args, [
        'vcenter_template',
        'vcenter_pool',
        'vcenter_folder',
        'vcenter_datastore'
    ])

    task = None
    try:
        task = clone(
            content,
            args.vcenter_template,
            args.vcenter_pool,
            args.vcenter_folder,
            args.vcenter_datastore
        )

        status = ((task is not None) and
            wait_for_task(task))
    
    except KeyboardInterupt:
        if ((task is not None) and
            task.info.cancelable):

            task.CancelTask()
            stderr.write(u'Errror: task canceled!\n')
    else:
        return status
    return False


def configure(content, args):

    test_args(args, [
        'guest_username',
        'allowed_groups',
        'allowed_users'
    ])

    set_password(
        args,
        args.guest_username,
        'guest_password'
    )

    vm_mor = get_object(content, vim.VirtualMachine, args.name)
    if vm_mor is None:
        stderr.write(u"Error: Virtual machine {} not found!\n".format(args.name))
        exit(1)

    if not wait_for_tools(vm_mor):
        stderr.write(u'Error: Virtual machine guest tools not ready!\n')
        exit(1)
    
    address = wait_for_ip_address(vm_mor)
    if not address:
        stderr.write(u'Error: Unable to obtain virtual machine guest IP address!\n')
        exit(1)

    print(u'Info: Connecting to guest over ssh'))
    # TODO: try/except
    guest = SSHGuest(address, args.guest_username, args.guest_password)
    print(u"Info: Connected to guest on IP address: {}".format(address))

    if guest.upgrade():
        print(u'Info: Guest system updated')
    else:
        stderr.write(u'Error: Updating guest system!\n')

    if guest.set_hostname(args.name):
        print(u'Info: Configured guest hostname')
    else:
        stderr.write(u'Error: Updating guest hostname!\n')

    for group in args.allowed_groups:
        if not guest.permit_group(group:
            stderr.write(u'Error: Adding group logon rights!\n')
            break

    for user in args.allowed_users:
        if not guest.permit_user(user):
            stderr.write(u'Error: Adding user logon rights!\n')
            break


class CFile(object):

    def __init__(self, file_name='config.ini', section='global'):
        self.file_name = file_name
        self.section = section

        self.parser = SafeConfigParser()
        self.is_ready = self.read()

    def __getattr__(self, attrname):

        try:
            attr = self.parser.get(
                self.section, attrname
            )
        
        except NoOptionError:
            return None

        return attr

    def get_multy_val_attr(self, attrname):

        attr = self.__getattr__(attrname)
        if attr is not None:
            return [val.strip() for val in attr.split(',')]

    def read(self):

        try:
            with open(self.file_name) as fo:
                self.parser.readfp(fo)
        
        except IOError:
            return False
        return self.parser.has_section(self.section)


def set_password(args, username, attrname, prompt=u"{}'s password: "):
    if ((attrname not in args) or
        not getattr(args, attrname)):

        password = getpass(prompt.format(username))
        if not password:
            stderr.write(u'Error: password required!\n')
            exit(1)
        
        setattr(args, attrname, password)


def add_arguments(subparsers, call):
    parser = subparsers.add_parser(
        call.func_name
    )
    parser.set_defaults(call=call)
    
    parser.add_argument('name')

    parser.add_argument('--vcenter_host')
    parser.add_argument('--vcenter_username')
    parser.add_argument('--vcenter_password')

    return parser


if __name__ = '__main__':
    parser = ArgumentParser()

    config = CFile()

    if config.read():

        parser.set_defaults(vcenter_host=config.vcenter_host)
        parser.set_defaults(vcenter_username=config.vcenter_username)
        parser.set_defaults(vcenter_password=config.vcenter_password)

        parser.set_defaults(vcenter_pool=config.vcenter_pool)
        parser.set_defaults(vcenter_folder=config.vcenter_folder)
        parser.set_defaults(vcenter_datastore=config.vcenter_datastore)
        parser.set_defaults(vcenter_template=config.vcenter_template)

        parser.set_defaults(allowed_users=config.get_multy_val_attr('allowed_users'))
        parser.set_defaults(allowed_groups=config.get_multy_val_attr('allowed_groups'))

    subparsers = parser.add_subparsers()

    subparser = add_arguments(subparsers, deploy)
    subparser.add_argument('--vcenter_pool')
    subparser.add_argument('--vcenter_folder')
    subparser.add_argument('--vcenter_datastore')
    subparser.add_argument('--vcenter_template')

    subparser = add_arguments(subparsers, configure)
    subparser.add_argument('guest', choices=['linux'])
    subparser.add_argument('--guest_username')
    subparser.add_argument('--guest_password')
    subparser.add_argument('--allowed_users', action='append', default=list())
    subparser.add_argument('--allowed_groups', action='append', default=list())

    args = parser.parse_args()

    test_args(args, [
        'vcenter_username',
        'vcenter_host'
    ])

    set_password(
        args,
        args.vcenter_username,
        'vcenter_password'
    )

    content = get_content(
        args.vcenter_username,
        args.vcenter_password,
        args.vcenter_host
    )

    if not content:
        stderr.write(u'Error: connecting to vCenter!\n')
        exit(1)

    args.call(content, args)
