#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# autor: Filip Varga

from records import records
from sys import stderr, exit
from datetime import datetime
from argparse import ArgumentParser, ArgumentTypeError

vendor_id = "2b80a53a-4f08-4f6d-9a38-cfdd43e0c0a8"
appbundle = "eu.mobile_alerts.weatherhub"
server = "measurements.mobile-alerts.eu"

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Nespravny datum: '{}'.".format(s)
        raise ArgumentTypeError(msg)

def fun1(db, args):
    with records(db) as ro:
        ro.update(args.datum, server, vendor_id,
        args.device_id, appbundle)

def fun2(db, args):
    with records(db) as ro:
        for record in ro.get(args.datum):
            print("{}, {}".format(record.datetime, record.measurement))

def cli():
    now = datetime.now()
    parser = ArgumentParser()
    
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser("update",
    help="Aktualizacia lokalnej databazy.")
    subparser.add_argument("-i", "--device-id",
    help="ID zariadenia", required=True)
    subparser.add_argument("-d", "--datum",
        help="Datum vo formate YYYY-MM-DD",
        type=valid_date,
        default=datetime(now.year, now.month, now.day))
    subparser.set_defaults(fun=fun1)

    subparser = subparsers.add_parser("zobraz",
    help="Zobrazenie zaznamov za dany den.")
    subparser.add_argument("-i", "--device-id",
    help="ID zariadenia", required=True)
    subparser.add_argument("-d", "--datum",
        help="Datum vo formate YYYY-MM-DD",
        type=valid_date,
        default=datetime(now.year, now.month, now.day))
    subparser.set_defaults(fun=fun2)

    return parser.parse_args()

def main():
    args = cli()
    args.fun("{}.db".format(args.device_id), args)

if __name__ == "__main__": main()
