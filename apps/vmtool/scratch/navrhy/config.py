#!/usr/bin/env python2.7

from ConfigParser import SafeConfigParser, \
    NoOptionError, NoSectionError, RawConfigParser
from argparse import Namespace
from os import environ


# TODO: test if file && section exists before reading

# TODO: Namesapce podporuje 'x' in namespace
# ja to ale nepodporujem !! pre specialne objekty
# spravo dedicny overwrite na toto testovanie, a 
# nepotrebujes hassattr
class NewConfig(Namespace):

    def __init__(self, file='config.ini', section='global'):
        self._config = SafeConfigParser()
        self._section = section
        self._file = file

    def __getattr__(self, attrname):
        try:
            value = environ.get(attrname,
                self._config.get(self._section,
                attrname))
        except NoOptionError:
            raise AttributeError(attrname)
        return value

    def __contains__(self, attrname):
        return self._config.has_option(
            self._section ,attrname) or \
            super(NewConfig, self).__contains__(attrname)

    def read(self):
        try:
            with open(self._file) as fo:
                self._config.readfp(fo)
        except IOError:
            return False
        return self._config.has_section(
            self._section)

    @property
    def mail(self):
        return '%s@%s' % (self.windows_username,
            self.windows_domain)


class Config(Namespace):

    def __init__(self, file):
        self._store = dict()
        self._config = RawConfigParser(
            allow_no_value=True)
        self._config.read(file)
    
    def _getone(self, prop):
        return environ.get(prop,
        self._config.get('global', prop))

    def _getter(self, prop):
        if self._store[prop]:
            return self._store[prop]
        return self._getone(prop)

    # DEBUG: nezobrazuje ale vsetko !
    def __str__(self):
        string = str()
        string += '\nConfig:\n'
        for key in self._store.keys():
            string += '%s: %s\n' % (key,
            self._getone(key))
        return string

    @property
    def host(self):
        return self._getter('vcenter_host')

    @host.setter
    def host(self, value):
        self._store['vcenter_host'] = value

    @property
    def domain(self):
        return self._getter('domain')

    @domain.setter
    def domain(self, value):
        self._store['domain'] = value

    @property
    def username(self):
        return self._getter('vcenter_username')

    @username.setter
    def username(self, value):
        self._store['vcenter_username'] = value

    @property
    def guest_username(self):
        return self._getter('guest_username')

    @guest_username.setter
    def guest_username(self, value):
        self._store['guest_username'] = value

    @property
    def pool(self):
        return self._getone('vcenter_pool')

    @property
    def folder(self):
        return self._getone('vcenter_folder')

    @property
    def datastore(self):
        return self._getone('vcenter_datastore')

    @property
    def linux(self):
        return self._getone('template_linux')

    @property
    def windows(self):
        return self._getone('template_windows')
        
    @property
    def mail(self):
        return '%s@%s' % (self.username, self.domain)

    # TODO: implementuj password getter !!!