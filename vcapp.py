import json
import hashlib
import os

from werkzeug.wrappers import Request, Response, BaseResponse
from werkzeug.exceptions import HTTPException
from werkzeug.contrib.securecookie import SecureCookie
from werkzeug.contrib.wrappers import JSONRequestMixin


class _Ser(object):

    @staticmethod
    def loads(byteslike):
        ustr = byteslike.decode("utf-8")
        return json.loads(ustr)

    @staticmethod
    def dumps(obj):
        s = json.dumps(obj, ensure_ascii=False)
        return s.encode("utf-8")


class JSONSecureCookie(SecureCookie):
    serialization_method = _Ser
    hash_method = staticmethod(hashlib.sha384)


class JSONRequest(Request, JSONRequestMixin):
    pass


class VCAppBase(object):

    def __init__(self, url_map, secret_key=None, session_kwargs=None):
        self.url_map = url_map
        self.secret_key = secret_key
        self.session_kwargs = session_kwargs or {}

    def view(self, endpoint, values, request, session, data):
        raise NotImplementedError

    def ctrl(self, endpoint, values, request, session):
        return getattr(self, "on_" + endpoint)(request, session, **values)

    def wsgi_app(self, environ, start_response):
        request = JSONRequest(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def dispatch_request(self, request):
        if self.secret_key:
            session = JSONSecureCookie.load_cookie(
                request, secret_key=self.secret_key)
        else:
            session = None
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            data = self.ctrl(endpoint, values, request, session)
            response = self.view(endpoint, values, request, session, data)
            if self.secret_key:
                session.save_cookie(response, **self.session_kwargs)
            return response
        except HTTPException as e:
            return e

    def json_response(self, data, **dumps_kwargs):
        ustr = json.dumps(**dumps_kwargs)
        return Response(ustr, mimetype="application/json")


class VCDBAppBase(VCAppBase):

    def view(self, endpoint, values, request, session, dbsession, data):
        raise NotImplementedError

    def ctrl(self, endpoint, values, request, session, dbsession):
        return getattr(self, "on_" + endpoint)(request, session, dbsession, **values)

    def get_dbsession(self):
        raise NotImplementedError

    def dispatch_request(self, request):
        if self.secret_key:
            session = JSONSecureCookie.load_cookie(
                request, secret_key=self.secret_key)
        else:
            session = None
        adapter = self.url_map.bind_to_environ(request.environ)
        dbsession = self.get_dbsession()
        try:

            endpoint, values = adapter.match()
            data = self.ctrl(endpoint, values, request, session, dbsession)
            response = self.view(endpoint, values, request,
                                 session, dbsession, data)
            if self.secret_key:
                session.save_cookie(response, **self.session_kwargs)
            return response
        except HTTPException as e:
            return e
        finally:
            dbsession.close()
