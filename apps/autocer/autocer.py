#!/usr/bin/env python2.7
# -*- encoding: utf-8 -*-
# author: Bc. Filip Varga

from os import system, remove, path, environ
from argparse import ArgumentParser
from sys import platform, argv


OPENSSL_CFG = '''
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
OPENSSL_CMD = 'openssl req -nodes -newkey rsa:2048 -out '\
              '"{0}.csr" -keyout "{0}.key" -config {1} {2}'


def openssl(args, config='.tmp.conf'):

    if args.subjectAltName:
        san = 'subjectAltName={}'.format(
            ','.join(['DNS:{}'.format(dns) for dns in args.subjectAltName]))
    else:
        san = ''

    with open(config, 'w') as fo:
        fo.write(OPENSSL_CFG.format(args, san))

    if args.debug:
        pipe = '2>&1'
    elif platform == 'win32':
        pipe = '> nul 2>&1'
    else:
        pipe = '&> /dev/null'

    rc = system(OPENSSL_CMD.format(args.commonName, config, pipe))
    remove(config)
    return rc


if __name__ == '__main__':

    DEFAULTS = {
        'C':  'SK',
        'L':  'Bratislava',
        'O':  'Urad geodezie kartografie a katastra Slovenskej republiky',
        'OU': 'IT'
    }

    def get_default(k):
        return environ.get('{}{}'.format(argv[0].upper(), k), DEFAULTS[k])

    def parse_args():
        parser = ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--countryName', default=get_default('C'))
        parser.add_argument('--localityName', default=get_default('L'))
        parser.add_argument('--organizationName', default=get_default('O'))
        parser.add_argument('--organizationUnitName', default=get_default('OU'))
        parser.add_argument('--subjectAltName', default=list(), action='append')

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--commonName')
        group.add_argument('--inputFile')

        return parser.parse_args()

    def print_status(rc, cn):
        print('[{0}] {1}\n\t{2}.csr, {2}.key'.format(
              "error" if rc else "success", path.abspath(path.curdir), cn))

    def main():
        args = parse_args()
        if args.inputFile:
            with open(args.inputFile) as fo:
                for line in fo.readlines():
                    args.commonName = line.rstrip()
                    print_status(openssl(args), args.commonName)
        else:
            print_status(openssl(args), args.commonName)

    main()
