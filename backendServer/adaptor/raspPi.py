#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This is adaptor for Raspberry PI GPIO controller
'''

import sys
import logging
import time
import pathlib
import threading
import fnmatch
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
        'green': 0,
        'amber': 0,
    }
else:
    import RPi.GPIO as GPIO
CHN = {
    'power': 26,
    'red': 23,
    'green': 25,
    'amber': 24,
}

class RaspPiAdaptor(PluginModule):
    subscribe_channels = []

    def __init__ (self, args, **kw) -> None:
        ''' init the module '''
        self.id = 'vid{}'.format(args.id)
        self.subscribe_channels = [
            'tester.{}.result'.format(self.id),
            'tester.{}.alert'.format(self.id),
        ]
        self.redis_conn = au.connect_redis_with_args(args)
        if not DEBUG:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO)
            for chn, pin in CHN.items:
                GPIO.setup(pin, GPIO.out)
                logging.debug('Set {} pin {} as output'.format(chn, pin))

        PluginModule.__init__(self,
            redis_conn=self.redis_conn
        )
        logging.debug('Init Raspberry Pi Adaptor with ID: {}'.format(self.id))
    
    def alert_switch_capture (self):
        ''' alert switch capture thread'''
        while True:

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
    
    def _stage_begin_capture (self, msg):
        ''' process begin capture message'''
        _status = msg.get('status', 'failed')
        if _status == 'success':
            _res = True
            for chn in ['red', 'green', 'amber']:
                self.set_gpio_status(chn, 'low')
                if _res:
                    _res = True is self.get_gpio_status(chn) == 0 else False
    
                



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
            self._stage_begin_capture(msg)

    def _process_alert_msg (self, msg):
        ''' process alert msg '''
        pass

    def start (self):
        ''' start raspberry pi module '''
        self._init_power()

        self.th_quit = threading.Event()
        self.th = threading.Thread(target=self.alert_switch_capture)
        self.th.start()

        self.stat_quit = threading.Event()
        self.stat = threading.Thread(target=self.status_update)
        self.stat.start()
    
    def set_gpio_status (self, chn, stat):
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

    def mod_close (self):
        ''' close the module '''
        self.th_quit.set()
        self.stat_quit.set()


if __name__ == '__main__':
    from adaptor import add_common_adaptor_args
    parser = au.init_parser('Raspberry Pi GPIO Control')
    add_common_adaptor_args(
        parser,
        id=1
    )
    args = au.parse_args(parser)

    rpa = RaspPiAdaptor(args=args)
    rpa.start()
    
    try:
        while not rpa.is_quit(1):
            pass
    except KeyboardInterrupt:
        #GPIO.cleanup()
        rpa.mod_close()