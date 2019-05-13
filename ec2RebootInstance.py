import json
import boto3

ec2 = boto3.client('ec2')
elb = boto3.client('elbv2')

regionMap = {
    "US East (N. Virginia)": "us-east-1",
}

def reboot_ec2(ec2_instance_id):
    try:
        response = ec2.reboot_instances(
            InstanceIds=[
                ec2_instance_id,
            ],
            DryRun=False
        )
        print(response)
        return response
        
    except Exception as err:
        print("Error occurred while restarting instance: {} ({})").format(ec2_instance_id, str(err))


def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    targetgroup_arn = "arn:aws:elasticloadbalancing:{}:{}:{}".format(
        regionMap[message['Region']],
        message['AWSAccountId'],
        message['Trigger']['Dimensions'][0]['value'])

    response = elb.describe_target_health(
        TargetGroupArn=targetgroup_arn,
    )

    for target in response['TargetHealthDescriptions']:
        if target['TargetHealth']['State'] == 'unhealthy':
            instance_id = target['Target']['Id']
            reboot_ec2(instance_id)
