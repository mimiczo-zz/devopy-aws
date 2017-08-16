#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by j on 2017. 7. 19..
import argparse
import datetime
import re
import traceback
from utils import ScriptUtils
from slack_webhook import SlackWebHooks

SEND_MESSAGES = []
# TODO : 80% 이상의 패턴을 체크, 숫자를 조절하여 메세지생성 조건을 변경할 수 있다 (80% -> 50%)
PERCENT_EXP = re.compile('.*([8-9])([0-9])%.*', re.DOTALL)
AWS_DESCRIBE_TARGET_PRIVATE_IP = 'aws ec2 describe-instances --filters {} --region={region} --profile={profile}'
# TODO : IP:PublicIpAddress -> IP:PrivateIpAddress 와 같이 내부IP 로 변경해서 사용할 수 있다
# TODO : searchTarget tagName setting
AWS_DESCRIBE_TARGET_FILTERS = '"Name=instance-state-name,Values=running" "Name=tag:Env,Values=production" --query "Reservations[].Instances[].{NAME:[Tags[?Key==\`Name\`].Value][0][0], TEAM:[Tags[?Key==\`Team\`].Value][0][0], IP:PublicIpAddress, DN:BlockDeviceMappings[0].DeviceName}"'
# TODO : setting instance run command and user name
SSH_MONITER_COMMAND = 'ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -i {} {}@{} "df -h -x tmpfs -x devtmpfs -x proc -x sysfs -x fusectl -x debugfs -x securityfs -x devpts -x pstore -x cgroup -x binfmt_misc"'


def init_argument():
    """
    Usage : ./moniter_instances_disk.py --profile=foo --region=ap-northeast-2 --slack=https://..../xxx/yyy/zzz

    :return:
    """
    global AWS_REGION
    global AWS_PROFILE
    global AWS_PEM_PATH
    global SLACK_WEBHOOK_KEY
    global SSH_MONITER_COMMAND
    parser = argparse.ArgumentParser(description='Foobar Moniter argument')
    parser.add_argument('--pem', metavar='pemfile path', required=True)
    parser.add_argument('--region', metavar='target_region_name', required=False, default='ap-northeast-2')
    parser.add_argument('--profile', metavar='aws_profiles', required=False, default='default')
    parser.add_argument('--slack', metavar='slack_webhooks_key', required=False)
    args = parser.parse_args()

    AWS_REGION = args.region
    AWS_PROFILE = args.profile
    AWS_PEM_PATH = args.pem
    SLACK_WEBHOOK_KEY = args.slack
    # slack
    SlackWebHooks.init_slack(SLACK_WEBHOOK_KEY)


def main():
    result = ScriptUtils.run_aws_cli_with_query(AWS_REGION, AWS_PROFILE, AWS_DESCRIBE_TARGET_PRIVATE_IP, AWS_DESCRIBE_TARGET_FILTERS)
    SEND_MESSAGES.append('>>>>> Start Time : {}\n>>>>> Monitor server disk is starting.'.format(datetime.datetime.now()))

    global IS_SEND_SLACK
    IS_SEND_SLACK = False

    for r in result:
        instance_user_name = 'ubuntu'
        if r['DN'].startswith('/dev/xvd'):
            instance_user_name = 'ec2-user'
        instance_ip = r['IP']
        instance_name = r['NAME']

        try:
            df_result = ScriptUtils.run_awscli(SSH_MONITER_COMMAND.format(AWS_PEM_PATH, instance_user_name, instance_ip), False)
        except:
            print(traceback.format_exc())
            df_result = ''

        if df_result and PERCENT_EXP.match(df_result):
            IS_SEND_SLACK = True
            SEND_MESSAGES.append('>>>>> Instance : [{}-{}]'.format(instance_name, instance_ip))
            SEND_MESSAGES.append(df_result)


if __name__ == "__main__":
    init_argument()

    try:
        main()
    except:
        print(traceback.format_exc())
    finally:
        print('\n'.join(SEND_MESSAGES))
        if IS_SEND_SLACK:
            SlackWebHooks.post_slack('\n'.join(SEND_MESSAGES), 'WARNING', '#FF0000')