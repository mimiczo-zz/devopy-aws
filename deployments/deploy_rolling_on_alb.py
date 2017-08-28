#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by j on 2017. 7. 19..
import argparse
import time
import datetime
import traceback
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from commons.utils import ScriptUtils
from commons.slack_webhook import SlackWebHooks

SENDMAIL_MESSAGES = []
AWS_HEALTHCHECK_COMMAND = 'aws elbv2 describe-target-health --target-group-arn {} --targets Id={},Port={} --query "TargetHealthDescriptions[].TargetHealth.State" --output text --region={region} --profile={profile}'
AWS_DEREGISTER_INSTANCE_COMMAND = 'aws elbv2 deregister-targets --target-group-arn {} --targets Id={} --region={region} --profile={profile}'
AWS_REGISTER_INSTANCE_COMMAND = 'aws elbv2 register-targets --target-group-arn {} --targets Id={} --region={region} --profile={profile}'
AWS_DESCRIBE_INSTANCE_COMMAND = 'aws ec2 describe-instances --instance-ids {} --query "Reservations[].Instances[]" --region={region} --profile={profile}'
AWS_DESCRIBE_TARGET_COMMAND = 'aws elbv2 describe-target-health --target-group-arn {} --query "TargetHealthDescriptions[].Target" --region={region} --profile={profile}'
AWS_DESCRIBE_TARGETGROUP_DELAY_SECOND_COMMAND = 'aws elbv2 describe-target-group-attributes --target-group-arn {} --query "Attributes[?Key==\'deregistration_delay.timeout_seconds\'].Value[]" --output text --region={region} --profile={profile}'
# TODO : setting instance run command and user name
SSH_DEPLOY_COMMAND = 'ssh -oStrictHostKeyChecking=no -i {} {}@{} "echo {} {}"'


def init_argument():
    """
    Usage : ./deploy_one_by_one_on_alb.py --pem=~/.ssh/foo.pem --name=foo-bar-targetgroup --appname=foo-bar --profile=aws --region=ap-northeast-2 --slack=https://.../xxx/yyy/zzz

    :return:
    """
    global AWS_REGION
    global AWS_PROFILE
    global AWS_PEM_PATH
    global SLACK_WEBHOOK_KEY
    global TO_EMAILS
    global TARGET_APPLICATION_NAME
    global TARGET_BUILD_NUMBER
    global TARGET_GROUP_ARN
    global RETRY_LIMIT
    parser = argparse.ArgumentParser(description='Deploy argument')
    parser.add_argument('--pem', metavar='pemfile path', required=True)
    parser.add_argument('--name', metavar='target_group_name', required=True)
    parser.add_argument('--appname', metavar='target_application_name', required=True)
    parser.add_argument('--buildnumber', metavar='target_build_number', required=True)
    parser.add_argument('--region', metavar='target_region_name', required=False, default='ap-northeast-2')
    parser.add_argument('--profile', metavar='aws_profiles', required=False, default='default')
    parser.add_argument('--slack', metavar='slack_webhooks_key', required=False)
    parser.add_argument('--retry', metavar='retry limit count', required=False, type=int, default=10)
    args = parser.parse_args()

    AWS_REGION = args.region
    AWS_PROFILE = args.profile
    AWS_PEM_PATH = args.pem
    TARGET_GROUP_ARN = args.name
    TARGET_APPLICATION_NAME = args.appname
    TARGET_BUILD_NUMBER = args.buildnumber
    SLACK_WEBHOOK_KEY = args.slack
    RETRY_LIMIT = args.retry
    # slack
    SlackWebHooks.init_slack(SLACK_WEBHOOK_KEY)


def get_target_group_info(target_groups_arn):
    """
    Run AWS CLI command with [elbv2 describe-target-health]

    :param target_groups_arn:
    :return: targetgroup.instance Id, Port, Privateip, Publicip
    """
    results = ScriptUtils.run_aws_cli_with_query(AWS_REGION, AWS_PROFILE, AWS_DESCRIBE_TARGET_COMMAND, target_groups_arn)
    ids, ips, ports = [], [], []
    for r in results:
        ids.append(r['Id'])
        ports.append(str(r['Port']))
        ips.append(get_instances_info(r['Id']))

    if results:
        return ids, ips, ports
    else:
        return None, None, None


def get_instances_info(instance_id):
    """
    Run AWS CLI command with [ec2 describe-instances]

    :param instance_id:
    :return: instance.PublicIpAddress, instance.PrivateIpAddress, instance.DeviceName
    """
    data = ScriptUtils.run_aws_cli_with_query(AWS_REGION, AWS_PROFILE, AWS_DESCRIBE_INSTANCE_COMMAND, instance_id)
    return {"PublicIpAddress": data[0]['PublicIpAddress'], "PrivateIpAddress": data[0]['PrivateIpAddress'], "DN": data[0]['RootDeviceName']}


def validation_init_status(instance_id, instance_port):
    """
    Run AWS CLI command with [elbv2 describe-target-health]

    :param instance_id:
    :param instance_port:
    :return:
    """
    status = ScriptUtils.run_aws_cli_with_query_to_string(AWS_REGION, AWS_PROFILE, AWS_HEALTHCHECK_COMMAND, TARGET_GROUP_ARN, instance_id, instance_port)
    if status != 'healthy':
        append_to_messages('\n======================================\nFirst Instances Status Not Healthy.\n======================================')
        raise Exception('\n======================================\nFirst Instances Status Not Healthy.\n======================================')


def deregist_targetgroup_for_instance(index, instance_id, instance_public_ip, instance_private_ip):
    """
    Run AWS CLI command with [elbv2 deregister-targets]

    :param instance_private_ip: 
    :param instance_public_ip: 
    :param index:
    :param instance_id:
    :return:
    """
    ScriptUtils.run_aws_cli_with_query(AWS_REGION, AWS_PROFILE, AWS_DEREGISTER_INSTANCE_COMMAND, TARGET_GROUP_ARN, instance_id)
    # ALB 제거 후에 request 유실될 확률이 있기때문에 대기시간을 주고 다음단계를 진행한다.
    append_to_messages_with_post_slack(
        '>>>>> Batch {}: Starting application deployment on instance(s) [{}]-[{}]-[{}]'.format(index, instance_id,
                                                                                               instance_public_ip,
                                                                                               instance_private_ip)
        + '\n>>>>> Batch {}: De-registering instance(s) from the alb-target-groups and waiting for them to go out of service'.format(index)
        + '\n>>>>> Batch {}: Waiting for Instance draining time [{} seconds]'.format(index, DEREGISTRATION_DELAY_SECOND), 'Deregist', '#FFE400')
    time.sleep(int(DEREGISTRATION_DELAY_SECOND))


def run_target_instance_deploy_command(index, instance_os_username, instance_ip):
    """
    Run CloudFormation Stack script(run-command.sh) for instance in target-groups

    :param instance_os_user: 
    :param index:
    :param instance_ip:
    :return:
    """
    ScriptUtils.run_shell(SSH_DEPLOY_COMMAND.format(AWS_PEM_PATH, instance_os_username, instance_ip, TARGET_APPLICATION_NAME, TARGET_BUILD_NUMBER))
    append_to_messages_with_post_slack('>>>>> Batch {}: Starting application deployment command execution'.format(index),
                                  'Running', '#FFBB00')


def regist_targetgroup_for_instance(index, instance_id):
    """
    Run AWS CLI command with [elbv2 register-targets]

    :param index:
    :param instance_id:
    :return:
    """
    ScriptUtils.run_aws_cli_with_query(AWS_REGION, AWS_PROFILE, AWS_REGISTER_INSTANCE_COMMAND, TARGET_GROUP_ARN, instance_id)
    append_to_messages_with_post_slack(
        '>>>>> Batch {}: Registering instance(s) with the alb-target-groups and waiting for them to be healthy'.format(
            index), 'Regist', '#ABF200')


def append_to_messages_with_post_slack(message, slack_title=None, slack_color=None):
    """
    SENDMAIL_MESSAGES append and post SlackWebHook

    :param message: string
    """
    append_to_messages(message)
    SlackWebHooks.post_slack(message, slack_title, slack_color)


def append_to_messages(message):
    """
    SENDMAIL_MESSAGES array append to message
    print message

    :param message: string
    """
    print(message)
    SENDMAIL_MESSAGES.append(message)


def alb_healthcheck(index, instance_id, instance_port):
    """
    do validation alb healthy status

    :param index:
    :param instance_id:
    :param instance_port:
    :return:
    """
    retry_count = 0
    while True:
        retry_count += 1
        try:
            status = ScriptUtils.run_aws_cli_with_query_to_string(AWS_REGION, AWS_PROFILE, AWS_HEALTHCHECK_COMMAND, TARGET_GROUP_ARN, instance_id, instance_port)
        except:
            status = 'unhealthy'

        append_to_messages('>>>>> Batch {}: Check Status is {}'.format(index, status))
        if status == 'healthy':
            break
        elif retry_count > RETRY_LIMIT:
            break

        time.sleep(5)

    if status == 'healthy':
        return True
    else:
        return False


def main():
    """
    main function

    1. 배포대상의 target-groups InstanceIds 를 조회
        for
        target_group 에 등록되어 있는 인스턴스목록을 배포처리한다.
        인스턴스 1대씩 동작하도록 설정

        2-1.  target-groups 에서 InstanceId 제거
        2-2.  Instance 배포대상 스크립트를 실행 (with ssh)
        2-3.  target-groups 에서 InstanceId 등록
        2-4.  target-groups 에서 InstanceId Status:healthy 여부 확인
        Status:healthy - 반복처리
        Status:unhealthy - 실패

    :return: void
    """
    # TODO : 퍼센트, 사용자설정에 따라서 자유도 있게 배포비율을 처리하도록 변경할수 있어야한다
    target_ids, target_ips, target_ports = get_target_group_info(TARGET_GROUP_ARN)

    # Target Group 설정된 대기시간(draining)을 가져온다.
    global DEREGISTRATION_DELAY_SECOND
    DEREGISTRATION_DELAY_SECOND = ScriptUtils.run_aws_cli_with_query_to_string(AWS_REGION, AWS_PROFILE, AWS_DESCRIBE_TARGETGROUP_DELAY_SECOND_COMMAND, TARGET_GROUP_ARN)

    if target_ids and len(target_ids) > 0:
        print('======================================================================================')
        append_to_messages_with_post_slack(
            '>>>>> Start Time : {}\n>>>>> Target is [{}] Environment update is starting.'.format(
                datetime.datetime.now(), TARGET_APPLICATION_NAME), 'Start', '#8C8C8C')
        for i in range(len(target_ids)):
            ##############################################
            #   parameter
            #   target_group_arn:   ALB 타켓그룹 ARN
            #   target_ids: 배포대상 인스턴스 id array
            #   target_ips: 배포대상 인스턴스 ip array
            #   target_ports: 배포대상 인스턴스 port array
            ##############################################
            index = i + 1
            instance_id = target_ids[i]
            instance_public_ip = target_ips[i]['PublicIpAddress']
            instance_private_ip = target_ips[i]['PrivateIpAddress']
            instance_device_name = target_ips[i]['DN']
            instance_port = target_ports[i]
            instance_os_username = 'ubuntu'
            if instance_device_name.startswith('/dev/xvd'):
                instance_os_username = 'ec2-user'

            # 최초 인스턴스 상태가 정상인지 체크
            # validation_init_status(instance_id, instance_port)

            # start deploy
            deregist_targetgroup_for_instance(index, instance_id, instance_public_ip, instance_private_ip)

            # 배포 대상서버에 private_ip 접속처리한다
            run_target_instance_deploy_command(index, instance_os_username, instance_private_ip)

            regist_targetgroup_for_instance(index, instance_id)

            is_succeed = alb_healthcheck(index, instance_id, instance_port)
            if not is_succeed:
                append_to_messages('\n======================================\nUnsuccessful command execution on instance id(s) [{}]\n======================================'.format(instance_id))
                raise Exception('\n======================================\nUnsuccessful command execution on instance id(s) [{}]\n======================================'.format(instance_id))

        append_to_messages_with_post_slack(
            '>>>>> Target is [{}] Environment update completed successfully.'.format(TARGET_APPLICATION_NAME),
            'Succeed', '#1DDB16')
        print('======================================================================================')
    else:
        append_to_messages('\n======================================\nNot Found TargetGroups Instances info.\n======================================')
        raise Exception('\n======================================\nNot Found TargetGroups Instances info.\n======================================')


if __name__ == "__main__":
    init_argument()

    try:
        main()
    except:
        append_to_messages_with_post_slack('>>>>> Target is [{}] Unsuccessful command execution. error message is [{}]'.format(TARGET_APPLICATION_NAME, traceback.format_exc()), 'Failed', '#FF0000')