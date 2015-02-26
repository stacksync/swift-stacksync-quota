'''
Created on 26 Feb 2015

@author: cotes
'''
import os
from swift.common.swob import wsgify, HTTPUnauthorized, HTTPBadRequest
import xmlrpclib
from swift.common.utils import get_logger
import json

class StackSyncQuotaMiddleware(object):
    def __init__(self, app, conf):
        self.app = app
        host = conf.get('stacksync_host', '127.0.0.1').lower()
        port = conf.get('stacksync_port', 61234)
        self.rpc_server = xmlrpclib.ServerProxy("http://"+host+":"+str(port))
        self.app.logger = get_logger(conf, log_route='stacksync_api')
        self.app.logger.info('StackSync Quota: Init OK')

    @wsgify
    def __call__(self, req):
        self.app.logger.info('StackSync Qutoa start')

        response = self.authorize(req)
        if response:
            return response
        
        return self.app
    
    def authorize(self, req):
        self.app.logger.info('StackSync API: authorize: path info: %s', req.path)
        if 'swift.authorize' in req.environ:
            resp = req.environ['swift.authorize'](req)
            del req.environ['swift.authorize']
            return resp
        return HTTPUnauthorized()


def filter_factory(global_conf, **local_conf):
    """Standard filter factory to use the middleware with paste.deploy"""
    conf = global_conf.copy()
    conf.update(local_conf)

    def stacksync_filter(app):
        return StackSyncQuotaMiddleware(app, conf)

    return stacksync_filter