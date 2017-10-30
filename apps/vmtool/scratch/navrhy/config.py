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

    def __init__(self, filename='config.ini', section='global'):
        self._filename = filename
        self._section = section
                
        self._config = SafeConfigParser()
        self.namespace = Namespace()

    def __getattr__(self, attrname):

        if attrname in self.namespace:
            attr = getattr(self.namespace, attrname)
            if attr is not None:
                return attr

        if attrname in environ:
            return environ.get(attrname)

        try:
            attr = self._config.get(self._section,
                attrname)

        except NoOptionError:
            raise AttributeError(attrname)

        return attr

    def __contains__(self, attrname):
        return (attrname in self.namespace) or \
            (attrname in environ) or \
            self._config.has_option(self._section,
            attrname)
        
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
