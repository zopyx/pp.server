# -*- coding: utf-8 -*-

from pyramid.httpexceptions import HTTPForbidden

def beta_token(request):
    beta_token = request.registry.settings.get('pp.beta_token')
    token_request = request.headers.get('pp-token')
    print token_request
    print beta_token
    if token_request != beta_token:
        raise HTTPForbidden
