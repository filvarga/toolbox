#!/usr/bin/env python2.7
# -*- encoding: utf-8 -*-
# autor: Bc. Filip Varga

from argparse import ArgumentParser
from ConfigParser import SafeConfigParser, \
    NoOptionError
from vmware import clone, \
    get_object, wait_for_task, \
    wait_for_tools, wait_for_ip_address
from sys import stderr


def deploy(content, args):

    # TODO: kontrola premennych

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


# TODO:
def configure(content, args):

    if args.guest == 'linux':
        pass
    


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
            return False
        
        setattr(args, attrname, password)
    
    return True


def add_arguments(subparsers, call):
    parser = subparsers.add_parser(
        call.func_name
    )
    parser.set_defaults(call=call)
    
    parser.add_argument('name')

    parser.add_argument('--vcenter_host')
    parser.add_argument('--vcenter_username')
    parser.add_argument('--vcenter_password', default=None)

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

    subparsers = parser.add_subparsers()

    subparser = add_arguments(subparsers, deploy)
    subparser.add_argument('--vcenter_pool')
    subparser.add_argument('--vcenter_folder')
    subparser.add_argument('--vcenter_datastore')
    subparser.add_argument('--vcenter_template')

    subparser = add_arguments(subparsers, configure)
    subparser.add_argument('guest', choices=['windows', 'linux'])
    subparser.add_argument('--guest_username')
    subparser.add_argument('--guest_password', default=None)

    args = parser.parse_args()

    if not set_password(
        args.vcenter_username,
        'vcenter_password'
    ):
        stderr.write(u'Error: password required!\n')
        exit(1)

    # TODO: kontrola parametrov:
    #   vcenter_username
    #   vcenter_host
    #   - vrat chybu cez ArgumentParser alebo nejak inteligentne
    #   napriklad informacia, ze nebola najdena hodnota premennej
    #   ani v konfigracnom subore (ak teda bol pouzity) ani vramci
    #   argumentu z prikazoveho riadku

    content = get_content(
        args.vcenter_username,
        args.vcenter_password,
        args.vcenter_host
    )

    if not content:
        stderr.write(u'Error: connecting to vCenter!\n')
        exit(1)

    args.call(content, args)
