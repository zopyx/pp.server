import plac
import json
import pprint
import requests
from datetime import datetime

@plac.annotations(
host=('Host', 'option'),
port=('Port', 'option'),
)
def service_client(html_filename, host='localhost', port=2222):
    data = unicode(open(html_filename, 'rb').read(), 'utf-8')
    payload = dict(html=data, 
                   callback_url='http://bing.com',
                   pdf_resolution='high')
    r = requests.post('http://%s:%s/new-conversion' % (host, port), data=json.dumps(payload))
    if r.status_code != 200:
        print 'An error occured: %s' % r.text
    else:
        pprint.pprint(json.loads(r.text))


def main():
    plac.call(service_client)

if __name__ == '__main__':
    main()
