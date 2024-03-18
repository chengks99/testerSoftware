#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This is wrapper for algo detection
'''
import sys
import logging
import pathlib
import threading
import serial

from plugin_module import PluginModule
from final_algo import TesterDetection

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
            'tester.{}.response'.format(self.id),
            'tester.{}.alert-response'.format(self.id),
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
    
#def read_from_usb(self, port='/dev/ttyUSB0/', baudrate=9600, timeout=1):
       # with serial.Serial(port, baudrate, timeout=timeout) as ser:
            #.sleep(2)
            #data = ser.readline().decode('utf-8').rstrip()
            #return data
    
    def wrapper (self):
        ''' wrapper to start algo code in thread'''
        while True:
            if self.algo is None:

                # self.algo = TesterDetection('/Users/juneyoungseo/Documents/Panasonic/test_videos/2023-12-29 08-08-11 SDU CT Tester.mp4', self.redis_conn, self.id)
                self.algo = TesterDetection("/dev/video0", self.redis_conn, self.id)
                #self.algo = TesterDetection(read_from_usb, self.redis_conn, self.id)))

            if self.th_quit.is_set():

                self.algo.close()
                break

    # def start_algo(self):
    #     self.algo = TesterDetection('/Users/juneyoungseo/Documents/Panasonic/test_videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4', self.redis_conn, self.id)


    def process_redis_msg (self, ch, msg):
        ''' process redis msg '''
        if ch in self.subscribe_channels:
            print (ch, msg)
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

    def _process_alert_response_msg (self, msg):
        ''' process alert response msg '''
        _stage = msg.get('stage', 'error')
        if _stage == 'alert-reset':
            self._response_alert_reset(msg)
        else:
            self._response_alert(msg)

    def _response_init (self, msg):
        ''' process init stage '''
        _status = msg.get('status', 'failed')

        if _status == 'success':
            self.algo.load_configuration()
        else:
            logging.error("Initialization Process Failed...")


    def _response_begin_capture (self, msg):
        _status = msg.get('status', 'failed')

        if _status == 'success':
            self.algo.capture_test_screen()
        else:
            logging.error("Capturing Process Failed...")

    def _response_test_screen (self, msg):
        _status = msg.get('status', 'failed')

        if _status == 'success':
            self.algo.start_mask_compare()
        else:
            logging.error("Test Screen Process Failed...")

    def _response_alert_reset (self, msg):
        _status = msg.get('status', 'failed')
        if _status == 'success':
            self.algo.set_alert_stage(msg.get('stage', 'alert-reset'), status=True)
        else:
            logging.error('Alert reset failed ...')

    def _response_alert (self, msg):
        _status = msg.get('status', 'failed')
        if _status == 'success':
            self.algo.set_alert_stage(msg.get('stage', 'alert-msg'), status=False)
        else:
            logging.error('Alert setting failed ...')

    # def close_algo(self):
    #     self.algo.close()
    def algo_close (self):
        ''' close the module '''
        self.th_quit.set()

if __name__ == "__main__":
    scriptPath = pathlib.Path(__file__).parent.resolve()
    sys.path.append(str(scriptPath.parent / 'backendServer/adaptor'))

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
