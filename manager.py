"""
配置信息:
1.数据库配置
2.redis配置
3.session配置: 主要是用来保存用户登陆信息(登陆的时候再来看)
4.csrf配置: 当修改服务器资源的时候保护(post,put,delete,dispatch)
5.日志文件: 记录程序运行的过程,如果使用print来记录,控制台没有保存数据,线上上线print不需要打印了.
6.迁移配置

"""""
import logging
import random
from datetime import datetime, timedelta

from info import create_app, db, models
from flask import current_app
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

# 调用方法,获取到app对象,app对象身上已经有配置相关信息了
from info.models import User

app = create_app('develop')

# 配置数据库迁移
manager = Manager(app)
Migrate(app, db)
manager.add_command('db', MigrateCommand)


# 使用装饰器@manager.option, 在通过终端调用的时候可以传递参数
@manager.option('-u', '--username', dest='username')
@manager.option('-p', '--password', dest='password')
def create_superuser(username, password):
    # 创建管理对象
    admin = User()

    # 设置属性
    admin.nick_name = username
    admin.mobile = username
    admin.password = password
    admin.is_admin = True

    # 保存到数据库
    try:
        db.session.add(admin)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return "创建失败"

    return "创建成功"


# 添加测试账号
@manager.option('-t', '--test', dest='test')
def create_test_user(test):
    # 定义用户容器
    user_list = []

    for i in range(0, 1000):
        # 创建对象
        user = User()

        # 设置属性
        user.nick_name = "138%08d" % i
        user.mobile = "138%08d" % i
        user.password_hash = 'pbkdf2:sha256:50000$JJDl1C8E$3074714998b4faf08d8493b2586734e57a892aefe78569b0060b2112404e0f4f'
        user.is_admin = False

        # 模拟用户近一个月的登录时间
        user.last_login = datetime.now() - timedelta(seconds=random.randint(0, 3600 * 24 * 31))

        # 添加到容器
        user_list.append(user)

    # 添加到数据库
    try:
        db.session.add_all(user_list)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return "添加失败"

    return "添加成功"


if __name__ == '__main__':
    manager.run()
