#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This is adaptor for Raspberry PI GPIO controller
'''

import sys
import logging
import time
import configparser
import pathlib
import threading
import datetime as dt

scriptPath = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(scriptPath.parent / 'common'))
import argsutils as au
from jsonutils import json2str

sys.path.append(str(scriptPath.parent / 'server'))
from plugin_module import PluginModule

DEBUG = True
if DEBUG:
    FAKE_STAT = {
        'power': 0,
        'red': 0,
        'amber': 0,
        'green': 0,
    }
else:
    import RPi.GPIO as GPIO
CHN = {
    'power': 26,
    'red': 23,
    'amber': 24,
    'green': 25,
}
ALERT_IN = {
    'alert': 6,
}
ALERT_OUT = {
    'pwm': 18,
}

class RaspPiController(PluginModule):
    def __init__ (self, args, **kw) -> None:
        ''' init the module '''
        self.id = 'vid{}'.format(args.id)
        self.subscribe_channels = [
            'tester.{}.result'.format(self.id),
            'tester.{}.alert'.format(self.id),
        ]
        self.housekeep_period = kw.pop('housekeep_period', 150)
        self.redis_conn = au.connect_redis_with_args(args)
        self.alert = False
        if not DEBUG:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO)
            for chn, pin in CHN.items:
                GPIO.setup(pin, GPIO.OUT)
                logging.debug('Set {} pin {} as output'.format(chn, pin))
            for chn, pin in ALERT_IN.items:
                GPIO.setup(pin, GPIO.IN)
                logging.debug('Set {} pin {} as alert input'.format(chn, pin))
            for chn, pin in ALERT_OUT.items:
                GPIO.setup(pin, GPIO.OUT)
                logging.debug('Set {} pin {} as alert output'.format(chn, pin))

        logging.debug('Init Raspberry Pi Adaptor with ID: {}'.format(self.id))
    
    def __str__ (self):
        return '<TESTER>'

    def get_info (self):
        ''' return a dict containing description of this module '''
        r = PluginModule.get_info(self)
        r.update({
            'plugin-modules': [m.component_name for m in self.plugin_modules]
        })
        return r

    def load_system_configuration (self, file_path):
        '''
            read configuration file and split configuration to cfg and plugins
            for plugin details in config file, it should start section by [plugin-(PLUGIN_NAME)]
        '''
        cfg_file = scriptPath.parent / file_path
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
        module_name = lambda m: 'procmod_' + m.replace('-', '_')
        self.plugin_modules = []
        cwd = scriptPath.parent / 'server'
        for key, val in self.plugins.items():
            if val.get('enabled', False):
                _path = val.get('path', None)
                if _path is None:
                    logging.debug('Plugin Module {} no path found'.format(key))
                    continue

                _fpath = cwd / _path
                if not _fpath.is_file():
                    logging.error('Plugin file not found: {}'.format(str(_fpath)))
                    continue
                
                spec = importlib.util.spec_from_file_location(module_name(key), str(_fpath))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.plugin_modules.append(
                    module.load_processing_module(
                        self.redis_conn, self.cfg, **extra_kw
                    )
                )
                logging.info('processing module {} loaded'.format(key))

    def start (self, **extra_kw):
        ''' start raspberry pi module '''
        self.load_system_configuration(self.args.cfg)
        PluginModule.__init__(self,
            redis_conn=self.redis_conn
        )
        self.start_listen_bus()
        self.load_plugin_modules(**extra_kw)

        self._init_power()

        self.start_thread('housekeep', self.housekeep)
        self.save_info()

        self.th_quit = threading.Event()
        self.th = threading.Thread(target=self.alert_switch_capture)
        self.th.start()

        self.stat_quit = threading.Event()
        self.stat = threading.Thread(target=self.status_update)
        self.stat.start()

    def _init_power (self):
        ''' init power light and update status '''
        self.set_gpio_status('power', 'low')       
        _status = 'success' if self.get_gpio_status('power') == 0 else 'failed'
        self.redis_conn.publish(
            'tester.{}.response'.format(self.id),
            json2str({
                'stage': 'init', 
                'status': _status,
                })
        )
        logging.debug('Init Power {}'.format(_status))

    def housekeep (self):
        ''' housekeeping thread '''
        while not self.is_quit(self.housekeep_period):
            for mod in self.plugin_modules:
                mod.housekeep()
            PluginModule.housekeep(self)

    def alert_switch_capture (self):
        ''' alert switch capture thread'''
        while True:
            if not DEBUG:
                if GPIO.input(ALERT_IN['alert']) == GPIO.HIGH:
                    if self.alert:
                        logging.debug('Switch pressed to reset alert')
                        self.alert_reset()
                    else:
                        logging.debug('Switch pressed to enable alert')
                        self._process_alert_msg(
                            {'stage': 'alert', 'status': 'activated'},
                            bySwitch=True
                        )
            if self.th_quit.is_set():
                break
    
    def status_update (self, interval=300):
        ''' status update for all IO on/off every {interval} seconds'''
        logging.debug('Status update every {}s'.format(interval))
        alertTime = dt.datetime.now()
        while True:
            currTime = dt.datetime.now()
            if currTime > alertTime:
                _dict = self.get_gpios_status()
                logging.debug('Status Message: {}'.format(_dict))
                self.redis_conn.publish(
                    'tester.{}.status'.format(self.id),
                    json2str(_dict)
                )
                alertTime = currTime + dt.timedelta(seconds=interval)
                logging.debug('Next status update time: {}'.format(alertTime))
            if self.stat_quit.is_set():
                break
            time.sleep(1)

    def process_redis_msg (self, ch, msg):
        ''' process redis message'''
        if ch in self.subscribe_channels:
            if ch == 'tester.{}.result'.format(self.id):
                self._process_result_msg(msg)
            if ch == 'tester.{}.alert'.format(self.id):
                self._process_alert_msg(msg)
    
    def _process_result_msg (self, msg):
        ''' process normal result msg'''
        _stage = msg.get('stage', 'error')
        if _stage == 'beginCapture':
            self._stage_change(msg, chns={'red': 'low', 'amber': 'low', 'green': 'low'})
        elif _stage == 'testScreen':
            self._stage_change(msg, chns={'red': 'high', 'amber': 'low', 'green': 'low'})
        elif _stage == 'popUp':
            self._stage_change(msg, chns={'red': 'high', 'amber': 'low', 'green': 'high'})

    def _process_alert_msg (self, msg, bySwitch=False):
        ''' process alert msg '''
        _status = msg.get('status', 'deactivate')
        _stage = msg.get('stage', 'error')
        if _stage == 'error':
            logging.error('Unable to determine stage {}'.format(_stage))
            return
        if _status == 'activated':
            _result = True
            self.set_gpio_status('amber', 'high')
            
            self._servo_change()

            _out = 'low' if self.get_gpio_status('amber') == 0 else 'high'
            if _out != 'high':
                _result = False
            logging.debug('[{}]: LED amber set to high: {}'.format(_stage, _result))
            self.redis_conn.publish(
                'tester.{}.alert-response'.format(self.id),
                json2str({
                    'stage': 'alert-switch' if bySwitch else 'alert-msg', 
                    'status': 'success' if _result else 'failed',
                    })
            )
            logging.debug('[{}] response: {}'.format(_stage, 'success' if _result else 'failed'))        

    def _stage_change (self, msg, chns={}):
        ''' process begin capture & test screen & pop up 
            chns format should be: {'key': 'low'|'high' ... }
        '''
        _status = msg.get('status', 'failed')
        _stage = msg.get('stage', 'error')
        if _stage == 'error':
            logging.error('Unable to determine stage {}'.format(_stage))
            return
        if _status == 'success':
            _result = True
            for chn, val in chns.items():
                self.set_gpio_status(chn, val)
                _out = 'low' if self.get_gpio_status(chn) == 0 else 'high'
                if _out != val: 
                    _result = False
                logging.debug('[{}]: LED {} set to {}: {}'.format(_stage, chn, val, _result))
            if _result: self.alert = True
            self.redis_conn.publish(
                'tester.{}.response'.format(self.id),
                json2str({
                    'stage': _stage, 
                    'status': 'success' if _result else 'failed',
                    })
            )
            logging.debug('[{}] response: {}'.format(_stage, 'success' if _result else 'failed'))
      
    def set_gpio_status (self, chn, stat):
        ''' set single gpio status '''
        if DEBUG:
            _stat = 0 if stat == 'low' else 1
            FAKE_STAT[chn] = _stat
        else:
            _stat = GPIO.LOW if stat == 'low' else GPIO.HIGH
            GPIO.output(CHN[chn], _stat)

    def get_gpio_status (self, chn):
        ''' get {chn} IO status'''
        if DEBUG:
            return FAKE_STAT[chn]
        else:
            return GPIO.input(CHN[chn])

    def get_gpios_status (self):
        ''' get all IO status'''
        _dict = {}
        for chn in CHN.keys():
            _dict[chn] = 'on' if self.get_gpio_status(chn) == 1 else 'off'
        return _dict
    
    def _servo_change (self):
        ''' change server stage when alert occured '''
        if DEBUG:
            logging.debug('Simulate servo rotation for alert accured')
        else:
            self.servo_th = threading.Thread(target=self.__alert_servo)
            self.servo_th.start()   

    def __alert_servo (self):
        ''' thread for servo process when alert occured '''
        a2d = lambda a : 100 - (2.5 + (12.0 - 2.5)/180*(a+90))

        _pwm = GPIO.PWM(ALERT_OUT['pwm'], 50)
        for d in [a2d(0), a2d(90), a2d(0)]:
            _pwm.start(d)
            time.sleep(2)
        _pwm.stop()

    def alert_reset (self):
        ''' reset alert when self.alert == True and switch pressed'''
        _result = True
        self.set_gpio_status('amber', 'low')
        _out = 'low' if self.get_gpio_status('amber') == 0 else 'high'
        if _out != 'low': _result = False
        logging.debug('[alert-reset]: LED amber set to low: {}'.format(_result))
        if _result: self.alert = False
        self.redis_conn.publish(
            'tester.{}.alert-response'.format(self.id),
            json2str({
                'stage': 'alert-reset',
                'status': 'success' if _result else 'failed',
            })
        )
        logging.debug('[alert-reset] response: {}'.format('success' if _result else 'failed',))
  
    def mod_close (self):
        ''' close the module '''
        if not DEBUG:
            GPIO.cleanup()
        self.th_quit.set()
        self.stat_quit.set()
    
    def close (self):
        ''' termination '''
        PluginModule.close(self)

if __name__ == '__main__':
    from adaptor import add_common_adaptor_args
    parser = au.init_parser('Raspberry Pi GPIO Control')
    add_common_adaptor_args(
        parser,
        id=1
    )
    args = au.parse_args(parser)

    rpi_ctrl = RaspPiController(args=args)
    rpi_ctrl.start()
    
    try:
        while not rpi_ctrl.is_quit(1):
            pass
    except KeyboardInterrupt:
        rpi_ctrl.mod_close()
        rpi_ctrl.close()