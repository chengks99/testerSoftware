#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from TesterDetection import TesterDetection

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

                # self.algo = TesterDetection('/Users/juneyoungseo/Documents/Panasonic/test_videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4', self.id, redis_conn=self.redis_conn)
                pass

            if self.th_quit.is_set():

                # if hasattr(self.algo, 'close'):
                #     self.algo.close()
                break

    def start_algo(self):
        self.algo = TesterDetection('/Users/juneyoungseo/Documents/Panasonic/test_videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4', self.redis_conn, self.id)


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

            self.algo.load_configuration()

        else:
            logging.error("Initialization Process Failed...")


    def _response_begin_capture (self, msg):
        _status = msg.get('status', 'failed')

        if _status == 'success':
            # FIXME call self.algo to process capture image
            # FIXME if self.algo success to start image capture, publish redis msg
            self.algo.video_capture()
        else:
            logging.error("Capturing Process Failed...")

    def _response_test_screen (self, msg):
        _status = msg.get('status', 'failed')

        if _status == 'success':
            # FIXME call self.algo to process capture image
            # FIXME if self.algo success to start image capture, publish redis msg
            self.algo.capture_test_screen()
        else:
            logging.error("Test Screen Process Failed...")

    def _respone_alert_reset (self, msg):
        _status = msg.get('status', 'failed')
        if _status == 'success':
            self.algo.set_alert_stage(msg.get('stage', 'alert-reset'), stage=True)
        else:
            logging.error('Alert reset failed ...')

    def _response_alert (self, msg):
        _status = msg.get('status', 'failed')
        if _status == 'success':
            self.algo.set_alert_stage(msg.get('stage', 'alert-msg'), stage=True)
        else:
            logging.error('Alert setting failed ...')

    def close_algo(self):
        self.algo.close()
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









        
# '''
# This is wrapper for algo detection
# '''
# import sys
# import logging
# import pathlib
# import threading

# from plugin_module import PluginModule
# from initial_algo import TesterDetection

# scriptPath = pathlib.Path(__file__).parent.resolve()
# sys.path.append(str(scriptPath.parent / 'common'))
# import argsutils as au
# from jsonutils import json2str

# class AlgoWrapper(PluginModule):
#     def __init__ (self, args, **kw) -> None:
#         ''' init module'''
#         self.id = 'vid{}'.format(args.id)
#         self.algo = None
#         self.subscribe_channels = [
#             'tester.{}.result'.format(self.id),
#             'tester.{}.alert'.format(self.id),
#         ]
#         self.redis_conn = au.connect_redis_with_args(args)

#         PluginModule.__init__(self,
#             redis_conn=self.redis_conn
#         )
#         self.start_listen_bus()
#         logging.debug('Init Algo Wrapper with ID: {}'.format(self.id))
    
#     def start_thread (self):
#         ''' start wrapper in thread'''
#         self.th_quit = threading.Event()
#         self.th = threading.Thread(target=self.wrapper)
#         self.th.start()
    
#     def wrapper_thread (self):
#         ''' wrapper thread to start algo code in thread'''
#         while True:
#             if self.algo is None:
#                 '''
#                     FIXME: call algo class and fit into self.algo
#                     self.algo = XXXX
#                 '''
#                 pass
#             if self.th_quit.is_set():
#                 '''
#                     FIXME: call close to the algo class
#                 '''
#                 break
    
#     def start (self):
#         ''' start wrapper '''
#         self.algo = TesterDetection(self.redis_conn, self.id)
    
#     def process_redis_msg (self, ch, msg):
#         ''' process redis msg '''
#         if ch in self.subscribe_channels:
#             if ch == 'tester.{}.response'.format(self.id):
#                 self._process_response_msg(msg)
#             if ch == 'tester.{}.alert-response'.format(self.id):
#                 self._process_alert_response_msg(msg)
    
#     def _process_response_msg (self, msg):
#         ''' process normal response msg '''
#         _stage = msg.get('stage', 'error')
#         if _stage == 'init':
#             self._response_init(msg)
#         elif _stage == 'beginCapture':
#             self._response_begin_capture(msg)
#         elif _stage == 'testScreen':
#             self._response_test_screen(msg)

#     def _process_alert_msg (self, msg):
#         ''' process alert response msg '''
#         _stage = msg.get('stage', 'error')
#         if _stage == 'alert-reset':
#             self._respone_alert_reset(msg)
#         else:
#             self._response_alert(msg)
    
#     def _response_init (self, msg):
#         ''' process init response stage '''
#         _status = msg.get('status', 'failed')
#         if _status == 'success':
#             self.algo.load_configuration()
#         else:
#             logging.error('Initialization process failed ... ')

#     def _response_begin_capture (self, msg):
#         ''' process begin capture response msg, make sure test screen ready '''
#         _status = msg.get('status', 'failed')
#         if _status == 'success':
#             self.algo.start_test_screen()
#         else:
#             logging.error('Begin Capture process failed ...')

#     def _response_test_screen (self, msg):
#         ''' process test screen response msg, start masking and comparison'''
#         _status = msg.get('status', 'failed')
#         if _status == 'success':
#             self.algo.start_mask_compare()
#         else:
#             logging.error('Test screen process failed ...')

#     def _respone_alert_reset (self, msg):
#         ''' process alert reset '''
#         _status = msg.get('status', 'failed')
#         if _status == 'success':
#             self.algo.set_alert_stage(msg.get('stage', 'alert-reset'), stage=True)
#         else:
#             logging.error('Alert reset failed ...')

#     def _response_alert (self, msg):
#         ''' process alert response msg '''
#         _status = msg.get('status', 'failed')
#         if _status == 'success':
#             self.algo.set_alert_stage(msg.get('stage', 'alert-msg'), stage=True)
#         else:
#             logging.error('Alert setting failed ...')
    
#     def algo_close_thread (self):
#         ''' close algo thread '''
#         self.algo.close()

#     def algo_close (self):
#         ''' close the module '''
#         self.th_quit.set()

# if __name__ == "__main__":
#     from adaptor import add_common_adaptor_args
#     parser = au.init_parser('Algo Wrapper')
#     add_common_adaptor_args(
#         parser,
#         id=1
#     )
#     args = au.parse_args(parser)

#     alw = AlgoWrapper(args=args)
#     alw.start()
    
#     try:
#         while not alw.is_quit(1):
#             pass
#     except KeyboardInterrupt:
#         alw.algo_close()
#         alw.close()
