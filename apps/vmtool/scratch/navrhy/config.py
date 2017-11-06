#!/usr/bin/env python2.7

from ConfigParser import SafeConfigParser, \
    NoOptionError, NoSectionError
from argparse import Namespace
from os import environ


# TODO: zvaz ci nevytvorit defaultny konfigurak
# pri kazdom spusteni v adresari, kde je program
# a ulozi parametre, ktore si vlozil ako vstupne
# argumenty

class Config(object):

    def __init__(self, namespace, filename='config.ini', section='global'):
        self._filename = filename
        self._section = section
                
        self._config = SafeConfigParser()
        self.namespace = namespace

    def __getattr__(self, attrname):
        attr = getattr(self.namespace,
            attrname, None)
        if attr:
            return attr

        attr = environ.get(attrname,
            None)
        if attr:
            return attr

        try:
            attr = self._config.get(self._section,
                attrname)
        
        except NoOptionError:
            raise AttributeError(attrname)

        return attr

    def __contains__(self, attrname):

        return ((getattr(self.namespace,
                attrname, None) is not None) or
                (attrname in environ) or
                self._config.has_option(self._section,
                attrname))
        
    def read(self):

        try:
            with open(self._filename) as fo:
                self._config.readfp(fo)

        except IOError:
            return False

        return self._config.has_section(self._section)

    @property
    def mail(self):
        return '%s@%s' % (self.windows_username,
            self.windows_domain)
