import json, os, logging
from time import sleep
import urllib.request, requests, np_db

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
root_domain = os.getenv('ROOT_DOMAIN')

# Caddy API call functions

# conf returns dict
# To ID by subdomain:
# caddy:2019/config/apps/http/servers/srv0/routes/<number>/match/0/host
def get_conf():
    conf = api(path='', method='GET')
    conf = json.dumps(conf)
    conf = json.loads(conf)
    return conf

# Example: add_reverse_proxy('sitful-hatred', host='nativeplanet.live', upstream='10.13.13.52:8080')
def add_reverse_proxy(subdomain, host=root_domain, upstream=None):
    remove_url(subdomain)
    logging.info(f'[Caddy]: Adding {subdomain}.{host} @ {upstream}')
    config = dict(
        match=[
            dict(
                host=[subdomain + '.' + host])
            ],
        terminal=True,
        handle=[
            dict(
                handler='reverse_proxy',
                upstreams=[dict(dial=upstream)])])
    config['@id'] = subdomain
    # api(path='apps/http/servers/srv0/routes', method='POST', data=config)
    api_post(path='apps/http/servers/srv0/routes', data=config)
    return True

def add_minio(subdomain, host=root_domain, upstream=None):
    remove_url(subdomain)
    port = np_db.get_value('services','port','subdomain',subdomain)
    logging.info(f'[Caddy]: Adding {subdomain}.{host} @ {upstream}')
    config = {
        'match':[
            {
            'host':[subdomain+'.'+host]
            }
        ],
        'terminal':True,
        'handle':[
            {
                'handler':'reverse_proxy',
                'headers':{
                    'request':{
                        'set':{
                            'Host':['{http.request.host}'],
                            'X-Forwarded-Host':['{http.request.host}'],
                            'X-Forwarded-Proto':['{http.request.proto}']
                        }
                    }
                },
                'upstreams':[{'dial':upstream}]
            }
        ]}
    config['@id'] = subdomain
    # api(path='apps/http/servers/srv0/routes', method='POST', data=config)
    api_post(path='apps/http/servers/srv0/routes', data=config)
    return True

# Example: add_filesrv('sitful-hatred', host='nativeplanet.live', upstream='/www')
def add_filesrv(subdomain, host=root_domain, upstream='/www'):
    remove_url(subdomain)
    config = dict(
        match=[
            dict(
                host=[subdomain+'.'+host])
        ],
        terminal=True,
        handle=[
            dict(
                handler='vars',
                root=upstream
            ),
            dict(
                browse=dict(),
                handler='file_server'
            )
    ])
    config['@id'] = subdomain
    logging.info(f'[Caddy]: Registering {subdomain}.{host} for static file server')
    api(path='apps/http/servers/srv0/routes', method='POST', data=config)
    return True

# Delayed switch from static placeholder to reverse proxy
def switch_to_proxy(sub,peer_addr):
    sleep(30)
    add_reverse_proxy(sub,root_domain,peer_addr)

# Find and remove any matching subdomains
def remove_url(sub):
    url = f'{sub}.{root_domain}'
    conf = get_conf()
    index = 0
    routes = []
    for route in conf['apps']['http']['servers']['srv0']['routes']:
        try:
            route_host = route['match'][0]['host'][0]
            if route_host == url:
                # api(path=f'apps/http/servers/srv0/routes/{index}', method='DELETE')
                routes.append(index)
                index += 1
            else:
                index += 1
        except AttributeError:
            index += 1
    for x in routes[::-1]:
        # api(path=f'apps/http/servers/srv0/routes/{x}', method='DELETE')
        api_del(path=f'apps/http/servers/srv0/routes/{x}')
    routecount = len(routes)
    if routecount >= 1:
        logging.info(f'[Caddy]: Removed {routecount} {url} subdomain route(s)')
    return routes

# Returns positive integer if match
def check_url(sub):
    url = f'{sub}.{root_domain}'
    conf = get_conf()
    index = 0
    count = 0
    for route in conf['apps']['http']['servers']['srv0']['routes']:
        try:
            route_host = route['match'][0]['host'][0]
            if route_host == url:
                count += 1
        except Exception as e:
            logging.exception(e)
    return count

# Return upstream
# Only returns first result
def check_upstream(sub,upstream):
    url = f'{sub}.{root_domain}'
    conf = get_conf()
    result = False
    for route in conf['apps']['http']['servers']['srv0']['routes']:
        try:
            route_host = route['match'][0]['host'][0]
            # If the route exists
            if route_host == url:
                dial = route['handle'][0]['upstreams'][0]['dial']
                if dial == upstream:
                    # If it's pointing at the right upstream
                    return True
                else:
                    result = False
            else:
                result = False
        except Exception as e:
            logging.exception(f'check_upstream: {sub} {upstream} {e}')
    return result

# Add 502 error handling page
# Adds to the whole server
def add_502():
    logging.info('[Caddy]: Adding error handling...')
    errors = dict(routes=[
        dict(
            handle=[
                dict(
                    handler='vars',
                    root='/www')]
            ),
            dict(
                group='group0',
                handle=[
                    dict(
                        handler='rewrite',
                        uri='/502.html'
                    )
                ],
                match=[
                    dict(
                        expression='{http.error.status_code} == 502'
                        )
                    ]
            ),
            dict(
                handle=[
                    dict(
                        handler='file_server',
                        hide=[
                            './Caddyfile'
                            ]
                    )
                ]
            )])
    api(path='apps/http/servers/srv0/routes', method='POST', data=errors)
    return True

# Basic API call pattern
def api(path='', method='GET', string=None, data=None):
    base_url = 'http://caddy:2019/config/'

    if string:
        data = string.encode('utf-8')
    elif data:
        data = json.dumps(data, indent=2).encode('utf-8')
    if data:
        req = urllib.request.Request(base_url + path, data=data, method=method)
    else:
        req = urllib.request.Request(base_url + path, method=method)

    req.add_header('Content-Type', f'application/json')
    try:
        # (req,timeout=3)
        with urllib.request.urlopen(req,timeout=8) as response:
            r = response.read().decode('utf-8')

            if response.status != 200:
                logging.warn(f'{path} ({response.status=})')
                return dict(message=f'Error HTTP Status {response.status}', path=path)

            if len(r) == 0:
                return dict(message=response.msg, path=path)

            return json.loads(r)

    except urllib.error.HTTPError as e:
        # status=500 returned for PUT value and other configuration errors
        return dict(message=str(e), path=path)
    
    except Exception as e:
        logging.exception(e)

    return dict(message='unknown error', path=path)

def api_post(path='',data=None):
    url = f'http://caddy:2019/config/{path}'
    headers = {"Content-Type": "application/json"}
    try:
        if data:
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            response = requests.post(url, headers=headers, timeout=10)
        print(response.status_code)
    except Exception as e:
        logging.exception(e)

def api_del(path='',data=None):
    url = f'http://caddy:2019/config/{path}'
    headers = {"Content-Type": "application/json"}
    try:
        if data:
            response = requests.delete(url, headers=headers, json=data, timeout=10)
        else:
            response = requests.delete(url, headers=headers, timeout=10)
        print(response.status_code)
    except Exception as e:
        logging.exception(e)