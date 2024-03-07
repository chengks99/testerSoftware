#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
backend server for Tester Software

Main jobs are:
1. load all plugin module
2. listen to all adaptor's status/events
3. distribute the status/event to plugin module
'''

import logging
import sys
import pathlib
import fnmatch
import configparser
import datetime as datetime

scriptPath = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(scriptPath.parent / 'common'))

import argsutils as au
from jsonutils import json2str
from plugin_module import PluginModule

class TesterSoftwareServer(PluginModule):

    # processing module base
    component_name = 'TESTER'
    subscribe_channels = ['tester.*.response', 'tester.*.alert-response']

    def __init__ (self, args, **kw) -> None:
        self.redis_conn = au.connect_redis_with_args(args)
        self.housekeep_period = kw.pop('housekeep_period', 150)
        self.cfg = {}
        self.plugins = {}
        self.plugin_modules = []
        PluginModule.__init__(self,
            redis_conn = self.redis_conn
        )
    
    def __str__ (self):
        return "<TESTER>"
    
    def get_info (self):
        ''' return a dict containing description of this module '''
        r = PluginModule.get_info(self)
        r.update({
            'plugin-modules': [m.component_name for m in self.plugin_modules]
        })
        return r
    
    def start (self, **extra_kw):
        ''' start tester server '''
        self.load_system_configuration(self.args.cfg)
        PluginModule.__init__(self,
            redis_conn=self.redis_conn
        )
        self.load_plugin_modules(**extra_kw)

        self.start_listen_bus()
        self.start_thred('housekeep', self.housekeep)
        self.save_info()

    def close (self):
        ''' terminate Tester Server '''
        PluginModule.close(self)
    
    def housekeep (self):
        ''' housekeeping thread '''
        while not self.is_quit(self.housekeep_period):
            for mod in self.plugin_modules:
                mod.housekeep()
            PluginModule.housekeep(self)

    def load_system_configuration (self, file_path):
        '''
            read configuration file and split configuration to cfg and plugins
            for plugin details in config file, it should start section by [plugin-(PLUGIN_NAME)]
        '''
        cfg_file = scriptpath.parent / file_path
        if cfg_file.is_file():
            config = configparser.ConfigParser()
            config.read(cfg_file)
            for section in config.sections():
                _params = None
                if 'plugin' in section:
                    if not section in self.plugins: self.plugins[section] = {}
                    _params = self.plugins[section]
                else:
                    if not section in self.cfg: self.cfg[section] = {}
                    _params = self.cfg[section]
                
                for key in config[section]:
                    if 'port' in key:
                        _params[key] = int(config[section][key])
                    elif key == 'enabled':
                        if fnmatch.fnmatch(config[section][key], '*rue'):
                            _params[key] = True
                        else:
                            _params[key] = False
                    else:
                        _params[key] = config[section][key]
        else:
            logging.error('Unable to locate config file at {}'.format(str(cfg_file)))
            self.close()
    
    def load_plugin_modules (self, **extra_kw):
        ''' load each plugin module and initialize them '''
        import importlib.util
        # get all enabled plugin modules and import each of them
        module_name = lambda m: 'procmod_' + m['_id'].replace('-', '_')
        self.plugin_modules = []
        cwd = scriptPath.parent / 'server'
        for key, val in self.plugins.items():
            _path = val.get('path', None)
            if _path is None:
                logging.debug('Plugin Module {} no path found'.format(key))
                continue

            _fpath = cwd / _path
            if not _fpath.is_file():
                logging.error('Plugin file not found: {}'.format(str(_fpath)))
                continue
            
            spec = importlib.util.spec_from_file_location(module_name(key), str(fpath))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.plugin_modules.append(
                module.load_processing_module(
                    self.redis_conn, self.db, au.to_namespace(self.cfg), **extra_kw
                )
            )
            logging.info('processing module {} loaded'.format(key))

if __name__ == "__main__":
    parser = au.init_parser('Tester Server', redis={})
    au.add_arg(parser, '--cfg', h='specify config file {D}', d='config.ini')
    args = au.parse_args(parser)

    svr = TesterSoftwareServer(args=args)
    svr.start()

    try:
        while not svr.is_quit(10):
            pass
    except KeyboardInterrupt:
        logging.info('Ctrl-C received -- terminating ...')
        svr.close()