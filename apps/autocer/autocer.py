#!/usr/bin/env python2.7
# -*- encoding: utf-8 -*-
# autor: Bc. Filip Varga

from argparse import ArgumentParser
from os import system, remove, path
from sys import platform
import sys


DEFAULT_C = 'SK'
DEFAULT_L = 'Bratislava'
DEFAULT_O = 'Urad geodezie kartografie a katastra Slovenskej republiky'
DEFAULT_OU = 'IT'
DEFAULT_CONFIG = '''
[ req ]
prompt = no
req_extensions = ext
distinguished_name = dn
[ dn ]
C={0.countryName}
L={0.localityName}
O={0.organizationName}
OU={0.organizationUnitName}
CN={0.commonName}
[ ext ]
basicConstraints=CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
{1}
'''


def openssl(args, config='.tmp.conf'):

    if args.subjectAltName:
        subjectAltName = 'subjectAltName={}'.format(
            ','.join(['DNS:{}'.format(dns) for dns in args.subjectAltName]))
    else:
        subjectAltName = ''

    with open(config, 'w') as fo:
        fo.write(DEFAULT_CONFIG.format(args, subjectAltName))

    if args.debug:
        pipe = '2>&1'
    elif platform == 'win32':
        pipe = '> nul 2>&1'
    else:
        pipe = '&> /dev/null'

    rcode = system('openssl req -nodes -newkey rsa:2048'\
        ' -out "{0}.csr"'\
        ' -keyout "{0}.key"'\
        ' -config {1} {2}'.format(
        args.commonName, config, pipe))

    remove(config)

    if rcode == 0:
        print('{0}.csr\n{0}.key'.format(
            path.join(path.abspath(path.curdir),
            args.commonName)))

    return rcode

if __name__ == '__main__':

    def parse_args():
        parser = ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--countryName', default=DEFAULT_C)
        parser.add_argument('--localityName', default=DEFAULT_L)
        parser.add_argument('--organizationName', default=DEFAULT_O)
        parser.add_argument('--organizationUnitName', default=DEFAULT_OU)
        parser.add_argument('--subjectAltName', default=list(), action='append')

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--commonName')
        group.add_argument('--inputFile')

        return parser.parse_args()

    def main():
        args = parse_args()
        if args.inputFile:
            with open(args.inputFile) as fo:
                for line in fo.readlines():
                    line = line.rstrip()
                    args.commonName = line
                    rcode = openssl(args)
                    print("{1}\t{0}".format("error" if rcode else "success",
                        line))

        else:
            rcode = openssl(args)
            print("{1}\t{0}".format("error" if rcode else "success",
                args.commonName))

    main()
