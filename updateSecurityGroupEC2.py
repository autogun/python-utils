import boto3
import requests
import sys
requests.packages.urllib3.disable_warnings()

check_url = 'https://api.ipify.org''
rule_desc = '<Rule-Desc-Here>'
security_groups = {
    'Group1': ['sg-abc', 'eu-west-1'],
    'Group2': ['sg-xyz' 'us-east-1']
}

def ruleAction(action, id, ip):
    response = getattr(main.security_group, action)(
        GroupId=id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
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

def main():
    try:
        current_ip = requests.get(check_url, timeout=10, verify=False).text.strip() + '/32'
    except requests.exceptions.Timeout as err:
        sys.exit('Check your intentet connection: {}'.format(err))

    session = boto3.session.Session()
    for grp_name, value in security_groups.iteritems():
        grp_id = value[0]
        grp_region = value[1]
        resource = session.resource('ec2', region_name=grp_region)
        client = session.client('ec2', region_name=grp_region)
        main.security_group = resource.SecurityGroup(grp_id)
        describe_sec_group = client.describe_security_groups(GroupIds=[grp_id])
        new_grp_detected = True
        for ip_ranges in describe_sec_group['SecurityGroups'][0]['IpPermissions']:
            for rule in ip_ranges['IpRanges']:
                if 'Description' in rule:
                    if rule['Description'] == rule_desc:
                        new_grp_detected = False
                        old_ip = rule['CidrIp']
                    else:
                        old_ip = None

                    if old_ip:
                        if old_ip == current_ip:
                            print '[INFO] "{}" is up-to-date'.format(grp_name)
                            break
                        else:
                            if (current_ip != old_ip):
                                print '[UPDATE] IP {} updated in "{}"'.format(current_ip, grp_name)
                                ruleAction('revoke_ingress', main.security_group.id, old_ip)
                                ruleAction('authorize_ingress', main.security_group.id, current_ip)

        if new_grp_detected:
            print '[NEW] IP {} added to "{}"'.format(current_ip, grp_name)
            ruleAction('authorize_ingress', main.security_group.id, current_ip)

if __name__ == '__main__':
    main()
