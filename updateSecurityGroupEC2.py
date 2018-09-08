import boto3
import requests
requests.packages.urllib3.disable_warnings()

current_ip = requests.get('https://api.ipify.org', timeout=10, verify=False).text.strip() + '/32'
rule_desc = '<Rule-Desc-Here>'
security_groups = {
    'Group1': 'sg-abc',
    'Group2': 'sg-xyz'
}

boto3.setup_default_session(profile_name='default', region_name='eu-west-1')
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')

def ruleAction(action, id, ip):
    response = getattr(security_group, action)(
        GroupId=id,
        IpPermissions=[
            {
                'IpProtocol': '-1',
                'FromPort': -1,
                'ToPort': -1,
                'IpRanges': [
                    {
                        'CidrIp': '{}'.format(ip),
                        'Description': rule_desc
                    }
                ]
            }
        ]
    )

    return response


for grp_name, value in security_groups.iteritems():
    security_group = ec2r.SecurityGroup(value)
    describe_sec_group = ec2c.describe_security_groups(GroupIds=[value])
    new_grp_detected = True
    for ip_ranges in describe_sec_group['SecurityGroups'][0]['IpPermissions']:
        for rule in ip_ranges['IpRanges']:
            if rule['Description'] == rule_desc:
                new_grp_detected = False
                old_ip = rule['CidrIp']
            else:
                old_ip = None

            if old_ip:
                if old_ip == current_ip:
                    print '[INFO] Security group {} is up-to-date'.format(grp_name)
                    break
                else:
                    if (current_ip != old_ip):
                        print '[UPDATE] IP {} update in security group {}'.format(current_ip, grp_name)
                        ruleAction('revoke_ingress', security_group.id, old_ip)
                        ruleAction('authorize_ingress', security_group.id, current_ip)

    if new_grp_detected:
        print '[NEW] IP {} added to security group {}'.format(current_ip, grp_name)
        ruleAction('authorize_ingress', security_group.id, current_ip)
