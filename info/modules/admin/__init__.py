from flask import Blueprint, request, session, redirect

admin_blu = Blueprint("admin", __name__, url_prefix='/admin')

from . import views


# 使用请求钩子,拦截所有访问admin_blu装饰的视图函数,都要经过该方法
@admin_blu.before_request
def before_request():
    # print("admin = %s"%request.url)
    # 判断访问的是否是,管理员登陆页面
    if not request.url.endswith('/admin/login'):
        # 判断是否是管理员
        if not session.get('is_admin'):
            return redirect('/')
