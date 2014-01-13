# -*- coding: utf-8 -*-

from pyramid.httpexceptions import HTTPForbidden

def token_auth(request):
    beta_token = request.registry.settings.get('pp.authentication_token')
    token_request = request.headers.get('pp-token')
    if token_request != beta_token:
        raise HTTPForbidden('Improper authorization token')
