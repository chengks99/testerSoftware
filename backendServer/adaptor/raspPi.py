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

class RaspPiAdaptor(PluginModule):
    def __init__ (self, args, **kw) -> None:
        ''' init the module '''
        self.id = 'vid{}'.format(args.id)
        self.subscribe_channels = [
            'tester.{}.result'.format(self.id),
            'tester.{}.alert'.format(self.id),
        ]
        self.redis_conn = au.connect_redis_with_args(args)
        self.alert = False
        if not DEBUG:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO)
            for chn, pin in CHN.items:
                GPIO.setup(pin, GPIO.out)
                logging.debug('Set {} pin {} as output'.format(chn, pin))

        PluginModule.__init__(self,
            redis_conn=self.redis_conn
        )
        self.start_listen_bus()
        logging.debug('Init Raspberry Pi Adaptor with ID: {}'.format(self.id))
    
    def alert_switch_capture (self):
        ''' alert switch capture thread'''
        while True:

            '''
                FIXME insert reading of switch GPIO
                if GPIO detect press, but self.alert is False, call _process_alert_msg({'stage': 'alert', 'status': 'activated'}, bySwitch=True)
                if GPIO detect press, but self.alert is True, call
                _alert_reset()
            '''

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
            self._stage_change(msg, chns={'red', 'high'})
        elif _stage == 'popUp':
            self._stage_change(msg, chns={'green': 'high'})

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
            '''
                FIXME: insert servo motor rotation
            '''
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
        if not DEBUG:
            GPIO.cleanup()
        rpa.mod_close()
        rpa.close()