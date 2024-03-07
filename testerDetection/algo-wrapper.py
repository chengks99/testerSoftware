#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This is wrapper for algo detection
'''
import sys
import logging
import pathlib
import threading

from plugin_module import PluginModule

scriptPath = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(scriptPath.parent / 'common'))
import argsutils as au
from jsonutils import json2str

class AlgoWrapper(PluginModule):
    def __init__ (self, args, **kw) -> None:
        ''' init module'''
        self.id = 'vid{}'.format(args.id)
        self.algo = None
        self.subscribe_channels = [
            'tester.{}.result'.format(self.id),
            'tester.{}.alert'.format(self.id),
        ]
        self.redis_conn = au.connect_redis_with_args(args)

        PluginModule.__init__(self,
            redis_conn=self.redis_conn
        )
        self.start_listen_bus()
        logging.debug('Init Algo Wrapper with ID: {}'.format(self.id))
    
    def start (self):
        ''' start wrapper '''
        self.th_quit = threading.Event()
        self.th = threading.Thread(target=self.wrapper)
        self.th.start()
    
    def wrapper (self):
        ''' wrapper to start algo code in thread'''
        while True:
            if self.algo is None:
                '''
                    FIXME: call algo class and fit into self.algo
                    self.algo = XXXX
                '''
                pass
            if self.th_quit.is_set():
                '''
                    FIXME: call close to the algo class
                '''
                break
    
    def process_redis_msg (self, ch, msg):
        ''' process redis msg '''
        if ch in self.subscribe_channels:
            if ch == 'tester.{}.response'.format(self.id):
                self._process_response_msg(msg)
            if ch == 'tester.{}.alert-response'.format(self.id):
                self._process_alert_response_msg(msg)
    
    def _process_response_msg (self, msg):
        ''' process normal response msg '''
        _stage = msg.get('stage', 'error')
        if _stage == 'init':
            self._response_init(msg)
        elif _stage == 'beginCapture':
            self._response_begin_capture(msg)
        elif _stage == 'testScreen':
            self._response_test_screen(msg)

    def _process_alert_msg (self, msg):
        ''' process alert response msg '''
        _stage = msg.get('stage', 'error')
        if _stage == 'alert-reset':
            self._respone_alert_reset(msg)
        else:
            self._response_alert(msg)
    
    '''
        FIXME: fill in operation for all response msg
    '''
    def _response_init (self, msg):
        ''' process init stage '''
        _status = msg.get('status', 'failed')
        if _status == 'success':
            #FIXME call self.algo to process capture image
            #FIXME if self.algo success to start image capture, publish redis msg
            self.redis_conn.publish(
                'tester.{}.result'.format(self.id),
                json2str({
                    'stage': 'beginCapture',
                    'status': 'success'
                })
            )

    def _response_begin_capture (self, msg):
        pass

    def _response_test_screen (self, msg):
        pass

    def _respone_alert_reset (self, msg):
        pass

    def _response_alert (self, msg):
        pass
    
    def algo_close (self):
        ''' close the module '''
        self.th_quit.set()

if __name__ == "__main__":
    from adaptor import add_common_adaptor_args
    parser = au.init_parser('Algo Wrapper')
    add_common_adaptor_args(
        parser,
        id=1
    )
    args = au.parse_args(parser)

    alw = AlgoWrapper(args=args)
    alw.start()
    
    try:
        while not alw.is_quit(1):
            pass
    except KeyboardInterrupt:
        alw.algo_close()
        alw.close()