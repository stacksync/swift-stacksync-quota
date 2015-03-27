
import os
from swift.common.swob import wsgify, HTTPUnauthorized
from swift.common.wsgi import make_pre_authed_request
from swift.common.utils import split_path
from swift.proxy.controllers.base import get_container_info, get_object_info

from util import create_response, is_valid_status, create_error_response

import xmlrpclib
from swift.common.utils import get_logger
import json
from client import Client

class StackSyncQuotaMiddleware(object):
    def __init__(self, app, conf):
        self.app = app
        host = conf.get('stacksync_quota_host', '127.0.0.1').lower()
        port = int(conf.get('stacksync_quota_port', 62345))
#         user = conf.get('omq_user', 'guest')
#         password = conf.get('omq_pass', 'guest')
#         exchange = conf.get('omq_exchange', 'rpc_global_exchange')
#         self.binding_name = conf.get('binding_name', 'IOmqQuotaHandler')
        self.app.logger = get_logger(conf, log_route='stacksync_quota')
        self.rpc_server = xmlrpclib.ServerProxy("http://"+host+":"+str(port))
        self.app.logger.info('StackSync Quota: Init OK')
#         env = {'user': user, 'pass': password, 'host' : host, 'port': port, 'exchange': exchange}
#         self.client = Client(env)

    @wsgify
    def __call__(self, req):
        self.app.logger.info('StackSync Quota start')
        self.app.logger.info(req.environ)
        
        #Check if is a call to object
        _, _, container, swift_object = split_path(req.path, 0, 4, True)
        if not swift_object:
            return self.app
        
        #check if is an authorize reqeuest
        container_info = get_container_info(req.environ, self.app, swift_source='CQ')
        response = self.authorize(req, container_info)
        if response:
            return response
        
        #check if is a valid request
        if not self.valid_request(req):
            # We only want to process PUT and DELETE requests
            return self.app


        quota_info = self.rpc_server.XmlRpcQuotaHandler.getAvailableQuota(container)

        response = create_response(quota_info, status_code=200)
        
        if not is_valid_status(response.status_int):
            self.app.logger.error("StackSync Quota: status code: %s. body: %s", str(response.status_int), str(response.body))
            return response
        
        quota_info = json.loads(quota_info)
        
        if req.method == 'PUT':
            return self.add_quota_used(quota_info, long(req.environ["CONTENT_LENGTH"]))
        if req.method == 'DELETE':
            return self.subtract_quota_used(quota_info, req.environ)                   
    
    def add_quota_used(self, quota_info, content_uploaded):
        quota_limit = long(quota_info['quota_limit'])
        quota_used = long(quota_info['quota_used'])
        quota_used_afer_put = quota_used + long(content_uploaded)
        
        quota_used_after_put = quota_used + content_uploaded
        if quota_used_after_put > quota_limit:
            self.app.logger.error("StackSync Quota: Quota exceeded. Available space: "+str(quota_limit-quota_used))
            return create_error_response(413, 'Upload exceeds quota.')

        #Notify quota_server for the new quota_used value.
        self.app.logger.info('StackSync Quota: add_quota_used')
        response = self.rpc_server.XmlRpcQuotaHandler.updateAvailableQuota(quota_info['user'], str(quota_used_after_put))
    
        response = create_response(response, status_code=200)
            
        if not is_valid_status(response.status_int):
            self.app.logger.error("StackSync Quota: Error updating quota used")
            return response
    
        return self.app
        
    def subtract_quota_used(self, quota_info, env):
        # HEAD to swift resource to know the content length
        quota_limit = long(quota_info['quota_limit'])
        quota_used = long(quota_info['quota_used'])
        
        object_info = get_object_info(env, self.app, env['PATH_INFO'])
        if not object_info or not object_info['length']:
            content_to_delete = 0
        else:
            content_to_delete = long(object_info['length'])
        
        quota_used_after_delete = quota_used - content_to_delete
        
        #send new quota to quota server
        self.app.logger.info('StackSync Quota: subtract_quota_used')
        response = self.rpc_server.XmlRpcQuotaHandler.updateAvailableQuota(quota_info['user'], str(quota_used_after_delete))
        
        response = create_response(response, status_code=200)
            
        if not is_valid_status(response.status_int):
            self.app.logger.error("StackSync Quota: Error updating quota used")
            return response
        
        return self.app
        
    def valid_request(self, req):
        if (req.method == 'PUT' or req.method == 'DELETE'):
            if not "HTTP_X_COPY_FROM" in req.environ.keys():
                return True                                                          
            return False
        return False
    
    def authorize(self, req, container_info):
        self.app.logger.info('StackSync Quota: authorize: path info: %s', req.path)
        if 'swift.authorize' in req.environ:
            req.acl = container_info['write_acl']
            response = req.environ['swift.authorize'](req)
            del req.environ['swift.authorize']
            if response:
                return response


def filter_factory(global_conf, **local_conf):
    """Standard filter factory to use the middleware with paste.deploy"""
    conf = global_conf.copy()
    conf.update(local_conf)

    def stacksync_filter(app):
        return StackSyncQuotaMiddleware(app, conf)

    return stacksync_filter
