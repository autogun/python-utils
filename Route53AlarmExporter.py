from botocore.exceptions import ClientError
import boto3
import json
import ipaddress

listOfAllowedNets = [
    '1.2.3.4/32',  # IP address space
]

STATUS_MAP = {
    'ALARM': 0,
    'OK': 1
}

outputHeader = '''
# TYPE aws_route53_health_check_status gauge
# HELP aws_route53_health_check_status CloudWatch metric AWS/Route53 HealthCheckStatus Dimensions: [HealthCheckId] Statistic: Minimum Unit: None
{}
'''

outputHealthcheck = 'aws_route53_health_check_status{{job="aws_route53",hostname="{}",customer="{}",health_check_id="{}",}} {}'

# https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#respond-to-load-balancer
def htmlReportHttpResponse(status, out):
    resp = {
        'statusCode': status,
        'statusDescription': '{} {}'.format(status, 'OK' if status is 200 else 'Forbidden'),
        'isBase64Encoded': False,
        'headers': {
            'Content-Type': 'text/plain; version=0.0.4'
        },
        'body': out
    }
    return resp

class DynamoDB(object):
    def __init__(self):
        try:
            self.dynamodb = boto3.resource('dynamodb')
            self.table = self.dynamodb.Table('cwAlarmExporter')
            self.r53 = boto3.client('route53')
        except ClientError as err:
            print('Failed to create boto3 resource. {}'.format(str(err)))
    
    def _isHealthCheckIdExists(self, hc_id):
        try: 
            self.r53.get_health_check(HealthCheckId=hc_id)
            return True
        except ClientError as err:
            if err.response['Error']['Code'] == 'NoSuchHealthCheck':
                print("HealthCheck {} does not exist".format(hc_id))
                return False

    def getCustomerTag(self, hc_id):
        try:
            response = self.r53.list_tags_for_resource(
                ResourceType='healthcheck',
                ResourceId=hc_id
            )
            tags = response['ResourceTagSet']['Tags']
            customer = None
            for tag in tags:
                if tag['Key'] == 'Name':
                    name = tag['Value']
                if tag['Key'] == 'Customer':
                    customer = tag['Value']
        
            yield name, customer

        except ClientError as err:
            print(err)

    def put(self, alarm_name, customer, hc_id, status):
        keyDict = {
            'HealthCheckId': hc_id,
        }
        item = self.table.get_item(
            Key=keyDict
        )
        item_exists = item.get('Item')
        if item_exists:
            print('[UPDATE] {} with status: {}'.format(alarm_name, status))
            self.table.update_item(
                Key=keyDict,
                # 'Status' is a reserved words in DynamoDB
                # ExpressionAttributeNames is used to workaround this.
                UpdateExpression='SET #status = :val1, Customer = :val2',
                ExpressionAttributeValues = {
                    ':val1': STATUS_MAP[status],
                    ':val2': customer
                },
                ExpressionAttributeNames = {
                    "#status": "Status"
                }
            )
        else:
            print('[NEW] {} added with status: {}'.format(alarm_name, status))
            self.table.put_item(
                Item = {
                    'HealthCheckId': hc_id,
                    'AlarmName': alarm_name,
                    'Customer': customer,
                    'Status': STATUS_MAP[status]
                }
            )

    
    def scan(self):
        response = self.table.scan()
        alarms = []
        for item in response['Items']:
            name    = item.get('AlarmName')
            cust    = item.get('Customer')
            hc_id   = item.get('HealthCheckId')
            status  = item.get('Status')
            # if status == int(0):
            #     if not self._isHealthCheckIdExists(hc_id):
            #         continue
            alarms.append(outputHealthcheck.format(name.lower(), cust, hc_id, float(status)))
        
        return(htmlReportHttpResponse(200, outputHeader.format('\n'.join(alarms))))


def isPrometheusScrapeRequest(event):
    http_method = event.get('httpMethod')
    if http_method is not None and http_method == 'GET' or http_method == 'HEAD':
        return True
    return False

def handlePrometheusScrapeRequest(event, db):
    accessed_ip = event['headers']['x-forwarded-for']
    for network in listOfAllowedNets:
        if ipaddress.IPv4Address(accessed_ip) in ipaddress.IPv4Network(network):
            print('Serving request from IP: {}'.format(accessed_ip))
            return(db.scan())

    print('Blocked request from untrusted IP: {}'.format(accessed_ip))
    return(htmlReportHttpResponse(403, "Not Authorized!"))

def isHealthCheckSnsRequest(event):
    if event['Records'][0]['EventSource'] == 'aws:sns':
        return True
    return False

def handleHealthCheckSns(event, db):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    health_check_id = message['Trigger']['Dimensions'][0]['value']
    status = message.get('NewStateValue')
    hc_tags = list(db.getCustomerTag(health_check_id))[0]
    alarm_name = hc_tags[0]
    customer = str(hc_tags[1])
    db.put(alarm_name, customer, health_check_id, status)

def lambda_handler(event, context):
    db = DynamoDB()
    if isPrometheusScrapeRequest(event):
        return(handlePrometheusScrapeRequest(event, db))
    elif isHealthCheckSnsRequest(event):
        handleHealthCheckSns(event, db)
