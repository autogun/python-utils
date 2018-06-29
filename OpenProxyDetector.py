from botocore.vendored import requests
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import asyncio
import boto3
import concurrent.futures
import json
import sys

DYNAMODB_TABLE = '<table_name>'
DYNAMODB_REGION = '<aws_region>'
URL_CHECK = 'http://example.com'
URL_CHECK_PAYLOAD = 'OK'
TO_EMAIL = '<to_email_address>'
FROM_EMAIL = 'OPEN PROXY DETECTOR <omg@alarm.com>'
REPLY_TO = '<reply_to_email_address>'

def send_email_ses(msg):
    client = boto3.client('ses')
    subject = 'ALARM: Open proxy detected'

    result = client.send_email(
        Source = FROM_EMAIL,
        Destination = {
            'ToAddresses': [TO_EMAIL]
        },
        Message = {
            'Subject': {
                'Data': subject,
                'Charset': 'utf8'
            },
            'Body': { 
                'Text': {
                    'Data': '\n'.join(msg),
                    'Charset': 'utf8'
                }
            }
        },
        ReplyToAddresses = [
            REPLY_TO
        ]
    )


def get_proxy_list():
    dynamodb = boto3.resource("dynamodb", region_name=DYNAMODB_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)

    scan = table.scan()
    hostnames_list = []
    for i in scan['Items']:
        hostnames_list += [x for x in i["hostnames"] if '<string>' not in x] # Exlude hostname with with specific string

    return hostnames_list
    
    
def req_get(proxyhost):
    try:
        proxies = { 'http': 'http://{}:8080'.format(proxyhost),
                    'https': 'http://{}:8080'.format(proxyhost) }
        user_agent_headers = [ {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'},
                            {'User-Agent': 'CloudOpenProxyDetector CPython/3.6.1' } ]
        requests.packages.urllib3.disable_warnings()
        bypassed_requests = []
        for headers in user_agent_headers:
            req = requests.get(URL_CHECK, proxies=proxies, headers=headers, timeout=2, verify=False)
            bypassed_requests.append({'host': proxyhost, 'status': (
                req.text[:30]), 'code': req.status_code, 'user-aget': headers['User-Agent']})
        print(bypassed_requests)
        return bypassed_requests
        
    except requests.exceptions.Timeout:
        print('Http GET request to {} timedout'.format(proxyhost))
        return [{'host': proxyhost, 'status': 'timeout'}]
        
    except requests.exceptions.RequestException as err:
        print('Http GET request to {} encountered an error: {}'.format(proxyhost, err))
        return [{'host': proxyhost, 'status': 'N/A'}]
        
        
async def run_openproxy_detect():
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        proxy_list = get_proxy_list()
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, req_get, host)
            for host in proxy_list
        ]
        openproxy_detected = []
        for response in await asyncio.gather(*futures):
            for item in response:
                if item.get('status') == URL_CHECK_PAYLOAD:
                    openproxy_detected.append(item.get('host'))
        
        if len(openproxy_detected) > 0:
            send_email_ses(openproxy_detected)
                

def main(*_):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_openproxy_detect())
    loop.close()
