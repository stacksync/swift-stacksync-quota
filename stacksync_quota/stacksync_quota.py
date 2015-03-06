
import os
from swift.common.swob import wsgify, HTTPUnauthorized, HTTPBadRequest
from util import create_response, is_valid_status, create_error_response

import xmlrpclib
from swift.common.utils import get_logger
import json
from client import Client

class StackSyncQuotaMiddleware(object):
    def __init__(self, app, conf):
        self.app = app
        host = conf.get('omq_host', '127.0.0.1').lower()
        port = int(conf.get('omq_port', 62345))
#         user = conf.get('omq_user', 'guest')
#         password = conf.get('omq_pass', 'guest')
#         exchange = conf.get('omq_exchange', 'rpc_global_exchange')
#         self.binding_name = conf.get('binding_name', 'IOmqQuotaHandler')
        self.rpc_server.XmlRpcSyncHandler.getAvailableQuota(req.environ["HTTP_X_USER"])     
        self.app.logger.info('StackSync Quota: Init OK')
#         env = {'user': user, 'pass': password, 'host' : host, 'port': port, 'exchange': exchange}
#         self.client = Client(env)

    @wsgify
    def __call__(self, req):
        self.app.logger.info('StackSync Quota start')
        self.app.logger.info(req.environ)

        #response = self.authorize(req)
        #if response:
        #    return response
        #for key in req.environ.keys():
        #    self.app.logger.info(key)
        
        #self.app.logger.info('user_id: '+str(req.environ['HTTP_X_USER_ID']))
        #self.app.logger.info('user: '+str(req.environ['HTTP_X_USER']))
        #self.app.logger.info('user_name: '+str(req.environ['HTTP_X_USER_NAME']))
        if self.valid_request(req):
            quota_info = self.rpc_server.XmlRpcHandler.getAvailableQuota(req.environ["HTTP_X_USER"])
            #quota_info = self.client.sync_call(self.binding_name, "getAvailableQuota", [req.environ["HTTP_X_USER"]])

            response = create_response(quota_info, status_code=200)
            
            if not is_valid_status(response.status_int):
                app.logger.error("StackSync Quota: status code: %s. body: %s", str(response.status_int), str(response.body))
                return response
            
            quota_info = json.loads(quota_info)
            
            if req.method == 'PUT':
                return self.add_quota_used(quota_info, req.environ["CONTENT_LENGTH"])
            if req.method == 'DELETE':
                return self.substract_quota_used(quota_info)
            
                                    
    
    def add_quota_used(self, quota_info, content_uploaded):
        quota_limit = quota_info['quota_limit']
        quota_used = quota_info['quota_used']
        
        quota_used_afet_put = quota_used + content_uploaded
        if quota_used_afet_put > quota_limit:
            return create_error_response(401, 'You have exceeded the maximum quota. Your available space is: '+(quota_limit-quota_used))
        else:
            #Notify quota_server for the new quota_used value.
            #self.rpc_server.XmlRpcHandler.updateAvailableQuota(quota_info['user'], quota_used_after_put)

            return self.app
        
    def substract_quota_used(self, quota_inf):
        # HEAD to swift resource to know the content length
        
        return self.app
        
    def valid_request(self, req):
        if (req.method == 'PUT' or req.method == 'DELETE'):
            return True                                                          
        
        return False
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
