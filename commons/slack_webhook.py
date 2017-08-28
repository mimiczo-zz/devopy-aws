#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by j on 2017. 7. 28..
import datetime
import json
import requests


class SlackWebHooks:
    """
    The SlackWebHooks makes Incoming WebHooks Calls to the `Slack Incoming WebHooks <https://foo.slack.com/apps/incoming-webhooks>`
    SlackWebHooks.Builder('https://hooks.slack.com/services/xxxxx/yyyyy/zzzzz')\
        .setPretext('ProjectName')\
        .setTitle('title')\
        .setTitleLink('http://foo.bar')\
        .setText('`hello` world')\
        .setColor('#36a64f')\
        .build().post()
    """

    def __init__(self, builder):
        self.__builder = builder

    @staticmethod
    def init_slack(slack_webhook_url, username='Devopy Slack Event'):
        """
        create SlackWebHook object and init data
    
        :return:
        """
        if slack_webhook_url:
            SlackWebHooks.__builder = SlackWebHooks.Builder(slack_webhook_url).setUsername(username)

    @staticmethod
    def post_slack(text=None, title=None, color=None):
        """
        send to slack webhook
    
        :param text:
        :param title:
        :param color:
        :return: void
        """
        try:
            SlackWebHooks.__builder.setColor(color) \
                .setTitle(title) \
                .setText(text) \
                .setTime(datetime.datetime.now()) \
                .build().post()
        except AttributeError:
            print('Please call init_slack method or SlackWebHooks.Builder')

    def post(self):
        """
        Request Post Slack WebHooks message
        :return: void
        """
        try:
            requests.post(self.__builder.getUrl(), data=json.dumps(self.__builder.getBody()))
        except Exception as e:
            print(e)

    class Builder:
        """
        SlackWebHooks Builder pattern.
        """

        def __init__(self, url):
            self.__url = url
            self.__username = None
            self.__pretext = None
            self.__title = None
            self.__title_link = None
            self.__text = None
            self.__env = 'production'
            self.__color = '#36a64f'
            self.__time = datetime.datetime.now()

        def setUsername(self, username):
            self.__username = username
            return self

        def setPretext(self, pretext):
            self.__pretext = pretext
            return self

        def setTitle(self, title):
            self.__title = title
            return self

        def setTitleLink(self, title_link):
            self.__title_link = title_link
            return self

        def setText(self, text):
            self.__text = text
            return self

        def setEnv(self, env):
            self.__env = env
            return self

        def setColor(self, color):
            if color:
                self.__color = color
            return self

        def setTime(self, time):
            if time:
                self.__time = time
            return self

        def getUrl(self):
            return self.__url

        def getBody(self):
            fields = [
                {
                    'title': 'End Time',
                    'value': str(self.__time.strftime('%Y/%m/%d %H:%M:%S')),
                    'short': True
                },
                {
                    'title': 'Environment',
                    'value': self.__env,
                    'short': True
                }
            ]
            attachment = {
                'pretext': self.__pretext,
                'title': self.__title,
                'title_link': self.__title_link,
                'text': self.__text,
                'color': self.__color,
                'fields': fields,
                'mrkdwn_in': [
                    'text',
                    'pretext',
                    'title'
                ]
            }
            return {'username': self.__username, 'attachments': [attachment]}

        def build(self):
            if not self.is_valid_message():
                raise Exception('Not found required parameter(url, value)')
            return SlackWebHooks(self)

        def is_valid_message(self):
            return False if not self.__url or not self.__text else True