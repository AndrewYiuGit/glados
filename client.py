#!/usr/bin/env python

import json
from importlib import import_module

import requests
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from ws4py.client.threadedclient import WebSocketClient

from plugin_base import DeclarativeBase as Base

SLACK_RTM_START_URL = 'https://slack.com/api/rtm.start?token={}'
SLACK_POST_MESSAGE_URL = 'https://slack.com/api/chat.postMessage'
PLUGINS_FILENAME = 'plugins.json'
DEBUG_CHANNEL_NAME = 'aperture-science'  # TODO: move this to a configuration file


class GladosClient(WebSocketClient):
    debug = False
    bot_users = []
    debug_channel = None
    general_channel = None
    async_plugins = {}

    def __init__(self, slack_token, **kwargs):
        if kwargs.get('debug', False):
            self.debug = True
            del kwargs['debug']
        self.token = slack_token
        wsdata = requests.get(SLACK_RTM_START_URL.format(slack_token)).json()
        url = wsdata['url']
        for user in wsdata['users']:
            if user['is_bot']:
                self.bot_users.append(user['id'])
        for channel in wsdata['channels']:
            if channel['name'] == DEBUG_CHANNEL_NAME:
                self.debug_channel = channel['id']
            if channel['is_general']:
                self.general_channel = channel['id']
        if self.debug:
            self.general_channel = self.debug_channel

        self.plugin_metadata = []
        self.plugins = []
        self.load_plugins()
        self.init_memory()
        self.init_plugins()
        return super().__init__(url, **kwargs)

    def opened(self):
        if self.debug:
            print('Hello!')

    def received_message(self, m):
        msg = json.loads(str(m))
        if 'user' in msg and msg['user'] in self.bot_users:
            return
        if self.debug:
            print(m)
            if 'channel' in msg and msg['channel'] != self.debug_channel:
                return
        else:
            if 'channel' in msg and msg['channel'] == self.debug_channel:
                return
        if 'ok' in msg:
            return
        for plugin in self.plugins:
            if plugin.can_handle_message(msg):
                plugin.handle_message(msg)
                if plugin.consumes_message:
                    return

    def closed(self, code, reason=None):
        self.session.commit()
        for plugin in self.plugins + list(self.async_plugins.values()):
            plugin.teardown()
        if self.debug:
            print('You monster')

    def init_memory(self):
        engine = sqlalchemy.create_engine('sqlite:///memory.db')
        Base.metadata.create_all(engine)
        Session = sessionmaker(engine)
        self.session = Session()

    def load_plugins(self):
        try:
            with open(PLUGINS_FILENAME) as plugins_file:
                plugins_dict = json.loads(plugins_file.read())
        except FileNotFoundError:
            print('Could not load plugins: file not found.')
            return
        except ValueError as e:
            print('Could not load plugins: malformed JSON:\n{0}'.format(e.args[0]))
        for module_name, class_dict in plugins_dict.items():
            try:
                module = import_module('plugins.{}'.format(module_name))
                self.plugin_metadata.append({
                    'name': class_dict['plugin_class'],
                    'class': getattr(module, class_dict['plugin_class']),
                    'type': class_dict['plugin_type']
                })
            except ImportError as e:
                print('Problem loading plugin {}:\n{}'.format(class_dict['plugin_class'], e))

    def init_plugins(self):
        for plugin_data in self.plugin_metadata:
            plugin_class = plugin_data['class']
            plugin_name = plugin_data['name']
            try:
                if plugin_data['type'] == 'normal':
                    self.plugins.append(plugin_class(self.session, self.post_message))
                elif plugin_data['type'] == 'async':
                    self.async_plugins[plugin_name] = plugin_class(self.session, self.post_general)
            except Exception as e:
                print('Problem initializing plugin {}:\n{}'.format(plugin_class.__name__, e))
        for plugin in self.plugins + list(self.async_plugins.values()):
            plugin.setup()

    def post_message(self, message, channel, attachments=None):
        # TODO: add default channel
        data = {
            'token': self.token,
            'channel': channel,
            'text': message,
            'as_user': True
        }
        if attachments is not None:
            data['attachments'] = json.dumps(attachments)
        response = requests.post(SLACK_POST_MESSAGE_URL, data=data)
        if self.debug:
            print(response)

    def post_general(self, message):
        self.post_message(message, self.general_channel)

    def handle_async(self, plugin, data):
        self.async_plugins[plugin].handle_message(data)


# For debugging
if __name__ == '__main__':
    try:
        token_file = open('.slack-token')
        token = token_file.read().strip()
        ws = GladosClient(token, debug=True)
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()
