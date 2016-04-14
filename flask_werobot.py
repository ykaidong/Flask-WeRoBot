#coding=utf-8
"""
Flask-WeRoBot
---------------

Adds WeRoBot support to Flask.

:copyright: (c) 2013 by whtsky.
:license: BSD, see LICENSE for more details.

Links
`````

* `documentation <https://flask-werobot.readthedocs.org/>`_
"""

__version__ = '0.1.2'

from werobot.robot import BaseRoBot
from flask import Flask

class WeRoBot(BaseRoBot):
    """
    给你的 Flask 应用添加 WeRoBot 支持。

    你可以在实例化 WeRoBot 的时候传入一个 Flask App 添加支持： ::

        app = Flask(__name__)
        robot = WeRoBot(app)

    或者也可以先实例化一个 WeRoBot ，然后通过 ``init_app`` 来给应用添加支持 ::

        robot = WeRoBot()

        def create_app():
            app = Flask(__name__)
            robot.init_app(app)
            return app
    
    """
    def __init__(self, app=None, endpoint='werobot', rule=None, *args, **kwargs):
        super(WeRoBot, self).__init__(*args, **kwargs)
        # 如果初始化进传入flask app, 调用init_app(), 否则需要手动调用
        if app is not None:
            self.init_app(app, endpoint=endpoint, rule=rule)
        else:
            self.app = None

    def init_app(self, app, endpoint='werobot', rule=None):
        """
        为一个应用添加 WeRoBot 支持。
        如果你在实例化 ``WeRoBot`` 类的时候传入了一个 Flask App ，会自动调用本方法；
        否则你需要手动调用 ``init_app`` 来为应用添加支持。
        可以通过多次调用 ``init_app`` 并分别传入不同的 Flask App 来复用微信机器人。

        :param app: 一个标准的 Flask App。
        :param endpoint: WeRoBot 的 Endpoint 。默认为 ``werobot`` 。
            你可以通过 url_for(endpoint) 来获取到 WeRoBot 的地址。
            如果你想要在同一个应用中绑定多个 WeRoBot 机器人， 请使用不同的 endpoint .
        :param rule:
          WeRoBot 机器人的绑定地址。默认为 Flask App Config 中的 ``WEROBOT_ROLE``
        """
        assert isinstance(app, Flask)
        from werobot.utils import check_token
        from werobot.parser import parse_user_msg
        from werobot.reply import create_reply

        self.app = app
        config = app.config
        token = self.token
        if token is None:
            # config的类继承自字典, setdefault()属于字典的方法
            # 如果键在字典中, setdefault()返回其值, 否则向字典中插入新键并设默认值
            token = config.setdefault('WEROBOT_TOKEN', 'none')
        if not check_token(token):
            raise AttributeError('%s is not a vailed WeChat Token.' % token)
        # 设置werobot的访问地址, 默认为 '/wechat'
        if rule is None:
            rule = config.setdefault('WEROBOT_ROLE', '/wechat')

        self.token = token

        from flask import request, make_response, abort

        def handler():
            if not self.check_signature(
                    request.args.get('timestamp', ''),
                    request.args.get('nonce', ''),
                    request.args.get('signature', '')
            ):
                return 'Invalid Request.'
            if request.method == 'GET':
                return request.args('echostr')

            body = request.data
            message = parse_user_msg(body)
            # get_reply() return the reply object for given message
            reply = self.get_reply(message)
            if not reply:
                return ''
            # flask将视图函数的返回值自动转为一个响应对像. 如果返回值是一个字符串
            # 它将被转换为以该字符串为主体的, 状态码为200, MIME类型是 text/html的响应对像.
            # flask 把返回值转为响应对像的逻辑如下:
            #   1. 如果返回值是一个合法的响应对像, 它会从视图直接返回
            #   2. 如果返回的是一个字符串, 响应对像会用字符串数据和默认参数创建
            #   3. 如果返回的是一个元组, 且元组中的元素可以提供额外的信息.
            #      这样的元组必须是 (response, status, headers) 形式, 且至少包含一个元素.
            #      status值会覆盖状态代码, headers可以是一个列表或者字典, 做为额外的消息标头值
            #   4. 如果上述条件均不满足, flask假设返回值是一个合法的WSGI应用程序,
            #      并转换为一个请求对像
            # 如果想在视图中操纵上述步骤结果的响应对像, 可以使用make_response()函数
            response = make_response(create_reply(reply, message=message))
            response.headers['content_type'] = 'application/xml'
            return response
        # 下面这个add_url_rule()的等效代码为:
        # @app.route(rule, methods = ['GET', 'POST'])
        # def handler()
        #    some_code...

        app.add_url_rule(rule, endpoint=endpoint,
                         view_func=handler, methods=['GET', 'POST'])
