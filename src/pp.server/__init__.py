from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.scan()
    config.add_route('job_status', '/status/{job_id}', request_method='GET')
    config.add_route('job_status_html', '/status-html/{job_id}', request_method='GET')
    return config.make_wsgi_app()
