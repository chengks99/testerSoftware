#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import ssl
import sys
import json
import fnmatch

try:
    from paho.mqtt import client as mqtt_client
except:
    print ('Error import library')
    pass

from plugin_module import PluginModule
from pathlib import Path
scriptpath = Path(__file__).parent.resolve()
sys.path.append(str(scriptpath.parent / 'common'))

class MQTTBroker(object):
    def __init__ (self, args) -> None:
        self.broker = args.get('broker', '')
        self.port = args.get('port', -1)
        self.topic = args.get('topic', '')
        if not self.__get_cert_path(args):
            logging.error('Unable to get all certificate files')
            exit(1)
        self.is_connected = False
        logging.debug('Connecting to MQTT broker {}:{} ...'.format(self.broker, self.port))
        self._connection()
        self._start()

    def __get_cert_path (self, args):
        _certDir = args.get('cert', '')
        self.cert = {
            'cert': scriptpath.parent / _certDir / args.get('pemcert', ''),
            'key': scriptpath.parent / _certDir /  args.get('pemkey', ''),
            'ca': scriptpath.parent / _certDir /  args.get('pemca', ''),
        }

        for k, v in self.cert.items():
            if v.is_file():
                self.cert[k] = str(v)
            else:
                return False
        return True

    def __get_context (self):
        try:
            # ssl_context = ssl.create_default_context()
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            # ssl_context.check_hostname = False
            # ssl_context.set_alpn_protocols(['http/1.1'])
            ssl_context.load_verify_locations(cafile=self.cert['ca'])
            ssl_context.load_cert_chain(certfile=self.cert['cert'], keyfile=self.cert['key'])
            logging.debug('SSL Context loaded')
            return ssl_context
        except Exception as e:
            logging.error('SSL Context failed: {}'.format(e))
            exit(1)

    def _connection (self):
        self.client = mqtt_client.Client('MQTTForwarding')
        USE_CONTEXT = True
        if USE_CONTEXT:
            self.client.tls_set_context(context=self.__get_context())
            self.client.tls_insecure_set(True)
        else:     
            logging.debug('Use MQTT TLS_set')
            self.client.tls_set(ca_certs=self.cert['ca'], certfile=self.cert['cert'], keyfile=self.cert['key'], tls_version=ssl.PROTOCOL_TLS)
            self.client.tls_insecure_set(False)
        logging.debug(ssl.OPENSSL_VERSION)
        self.client.on_connect = self._on_mqtt_connect
        self.client.connect(self.broker, self.port)
        logging.debug('Connected to MQTT Broker {}:{}'.format(self.broker, self.port))
    
    def _on_mqtt_connect (self, client, userdata, flags, rc):
        if rc == 0:
            #logging.debug('Connected to MQTT Broker {}:{}'.format(self.broker, self.port))
            self.is_connected = True
        else:
            logging.error('Reconnect to MQTT Broker {}:{}'.format(self.broker, self.port))
            self.is_connected = False
            self._connection()
    
    def _start (self):
        self.client.loop_start()
    
    def connection (self):
        return self.is_connected
           
    def get_msg (self, dataList):
        pass

    def publish (self, msg):
        # msg['Timestamp'] = int(dt.datetime.timestamp(msg['Timestamp']))
        self.client.publish(self.topic, json.dumps(msg), qos=0, retain=True)
        logging.info('MQTT message sent : {}'.format(msg))

    def close (self):
        self.client.disconnect()
        self.client.loop_stop()

class MQTTForwarding(PluginModule):
    component_name = 'mqtt-forward'
    subscribe_channels = ['tester.*.response', 'tester.*.alert-response', 'tester.*.status']

    def __init__ (self, redis_conn, args, **kw):
        self.redis_conn = redis_conn
        self.topic = args.get('topic', '')
        self.mqtt = MQTTBroker(args=args)
    
    def process_redis_msg (self, ch, msg):
        ''' redis message listener'''
        if ch in self.subscribe_channels:
            if fnmatch.fnmatch(ch, 'tester.*.response'):
                self._process_response_msg(ch.split('.')[1], msg)
            elif fnmatch.fnmatch(ch, 'tester.*.alert-response'):
                self._process_alert_response_msg(ch.split('.')[1], msg)
            elif fnmatch.fnmatch(ch, 'tester.*.status'):
                self._process_status_msg(ch.split('.')[1], msg)
    
    '''FIXME all process msg need to modify to meet MQTT format'''

    def _process_response_msg (self, vid, msg):
        ''' process normal response msg'''
        self.mqtt.publish(msg)

    def _process_alert_response_msg (self, vid, msg):
        ''' process alert response msg '''
        self.mqtt.publish(msg)
    
    def _process_status_msg (self, vid, msg):
        ''' process status msg'''
        self.mqtt.publish(msg)
    
    def close (self):
        self.mqtt.close()
        PluginModule.close(self)

def load_processing_module (*a, **kw):
    return MQTTForwarding(*a, **kw)

if __name__ == "__main__":
    raise Exception('This module must start with server')        