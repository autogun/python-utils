from botocore.exceptions import ClientError
import boto3
import json

OFFICE_IP = "<IP_ADDRESS/CIDR>"

session = boto3.Session(profile_name='infra', region_name='us-east-1')
client = session.client('ec2')

def add_ingress(group_id, proto, fromport, toport):
    try:
        data = client.authorize_security_group_ingress(
            DryRun=False,
            GroupId=group_id,
            IpPermissions=[
                {
                    'IpProtocol': proto,
                    'FromPort': fromport,
                    'ToPort': toport,
                    'IpRanges': [
                        {
                            'CidrIp': '1.2.3.4/32',
                            'Description': 'IP desc. goes here'
                        },
                        {
                            'CidrIp': '2.3.4.5/32',
                            'Description': 'IP desc. goes here'
                        },
                    ]
                }
            ]
        )
        print("Added to {}. Protocol: {}".format(group_name, proto))
    except ClientError as err:
        if 'Duplicate' in err.response['Error']['Code']:
            print("{} rules are already set".format(group_name))
        elif 'Unsupported IP protocol' in err.response['Error']['Message']:
            add_ingress(group_id, 'tcp', 0, 65535)
        else:
            print("{} error: {}".format(group_name ,err.response['Error']))

# Grab all possible regions
dict_regions = client.describe_regions()
regions = dict_regions['Regions']
regions_list = []
for region in regions:
    regions_list.append(region['RegionName'])

# regions_list = ['us-west-1']
for region in regions_list:
    print("== Region: {} ==".format(region))
    client = session.client('ec2', region_name=region)
    dict_sec_groups = client.describe_security_groups()
    sec_groups = dict_sec_groups['SecurityGroups']
    for group in sec_groups:
        group_name = group['GroupName']
        group_id = group['GroupId']
        rules = group['IpPermissions']
        for rule in rules:
            ipranges = rule['IpRanges']
            for ip in ipranges:
                if ip['CidrIp'] == OFFICE_IP:
                    print("Found relevant rule in {}".format(group_name))
                    add_ingress(group_id, '-1', -1, -1)
