import datetime

from flask import request, render_template, current_app, session, redirect, g, url_for, jsonify
import time
from info import user_login_data, constants, db
from info.models import User, News, Category
from info.utils.image_storage import image_storage
from info.utils.response_code import RET
from . import admin_blu

# 新闻分类,编辑/增加
# 请求路径: /admin/add_category
# 请求方式: POST
# 请求参数: id,name
# 返回值:errno,errmsg
@admin_blu.route('/add_category', methods=['POST'])
def add_category():
    """
    思路分析:
    1.获取参数
    2.校验,name即可,必有值
    3.根据分类编号判断,是增加,还是编辑
    4.返回响应
    :return: 
    """
    # 1.获取参数
    category_id = request.json.get('id')
    category_name = request.json.get('name')
    
    # 2.校验,name即可,必有值
    if not category_name: 
        return jsonify(errno=RET.PARAMERR,errmsg="参数不全")
    
    # 3.根据分类编号判断,是增加,还是编辑
    if category_id: #编辑
        
        #取出分类对象
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="查询分类失败")
    
        #判断分类是否存在
        if not category:
            return jsonify(errno=RET.NODATA,errmsg="分类不存在")
    
        #修改分类名称
        category.name = category_name
        
    else:#增加
        #创建分类对象,设置属性
        category = Category()
        category.name = category_name
        
        #提交到数据库
        try:
            db.session.add(category)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR,errmsg="保存分类失败")
        
        
    # 4.返回响应
    return jsonify(errno=RET.OK,errmsg="操作成功")


# 新闻分类列表
# 请求路径: /admin/news_category
# 请求方式: GET
# 请求参数: GET,无
# 返回值:GET,渲染news_type.html页面, data数据
@admin_blu.route('/news_category')
def news_category():
    """
    思路分析:
    1.查询所有分类信息
    2.转成字典列表
    3.携带数据,渲染页面
    :return:
    """
    # 1.查询所有分类信息
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="查询新闻分类失败")

    # 2.转成字典列表
    category_list = []
    for category in categories:
        category_list.append(category.to_dict())

    # 3.携带数据,渲染页面
    return render_template('admin/news_type.html',category_list=category_list)


# 新闻版式编辑,详情
# 请求路径: /admin/news_edit_detail
# 请求方式: GET, POST
# 请求参数: GET, news_id, POST(news_id,title,digest,content,index_image,category_id)
# 返回值:GET,渲染news_edit_detail.html页面,data字典数据, POST(errno,errmsg)
@admin_blu.route('/news_edit_detail', methods=['GET', 'POST'])
def news_edit_detail():
    """
    思路分析:
    1.第一次进来是GEt请求
    2.获取参数
    3.校验参数
    4.查询新闻新闻对象,判断新闻是否存在
    5.查询所有分类信息,转成字典数据
    6.携带,新闻数据,分类数据,渲染页面


    如果第二次提交进来,POST请求
    1.获取参数
    2.校验参数
    3.查询新闻新闻对象,判断新闻是否存在
    4.上传图片
    5.重写设置属性到新闻对象
    6.返回响应
    :return:
    """
    # 1.第一次进来是GEt请求
    if request.method == "GET":
        # 2.获取参数
        news_id = request.args.get('news_id')

        # 3.校验参数
        if not news_id: return jsonify(errno=RET.PARAMERR,errmsg="参数不全")

        # 4.查询新闻新闻对象,判断新闻是否存在
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="新闻查询失败")

        if not news: return jsonify(errno=RET.NODATA,errmsg="新闻不存在")

        # 5.查询所有分类信息,转成字典数据
        try:
            categories = Category.query.all()
            categories.pop(0)#弹出最新信息
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="分类查询失败")

        category_list = []
        for category in categories:
            category_list.append(category.to_dict())

        # 6.携带,新闻数据,分类数据,渲染页面
        return render_template('admin/news_edit_detail.html',news=news.to_dict(),category_list=category_list)

    
    # 如果第二次提交进来,POST请求
    # 1.获取参数,POST(news_id,title,digest,content,index_image,category_id)
    news_id = request.form.get('news_id')
    title = request.form.get('title')
    digest = request.form.get('digest')
    content = request.form.get('content')
    index_image = request.files.get('index_image')
    category_id = request.form.get('category_id')
    
    # 2.校验参数
    if not all([news_id,title,digest,content,index_image,category_id]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不全")
    
    # 3.查询新闻新闻对象,判断新闻是否存在
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="新闻查询失败")

    if not news: return jsonify(errno=RET.NODATA, errmsg="新闻不存在")
    
    # 4.上传图片
    try:
        image_name = image_storage(index_image.read())
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="七牛云上传异常")
    
    #4.1判断图片是否上传成功
    if not image_name: return jsonify(errno=RET.NODATA, errmsg="上传图片失败")

    # 5.重写设置属性到新闻对象
    news.title = title
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    news.category_id = category_id

    # 6.返回响应
    return jsonify(errno=RET.OK,errmsg="编辑成功")
    


# 新闻版式编辑列表
# 请求路径: /admin/news_edit
# 请求方式: GET
# 请求参数: GET, p, keyword
# 返回值:GET,渲染news_edit.html页面,data字典数据
@admin_blu.route('/news_edit')
def news_edit():
    """
    思路分析:
    1.获取参数
    2.参数类型转换
    3.分页查询
    4.获取分页对象属性,总页数,当前页,当前页对象
    5.对象列表转成字典列表
    6.拼接数据,渲染页面
    :return:
    """
    # 1.获取参数
    page = request.args.get('p',1)
    keyword = request.args.get("keyword")

    # 2.参数类型转换
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 3.分页查询
    try:

        #判断是否有搜索关键字
        filters = []
        if keyword:
            filters.append(News.title.contains(keyword))

        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,10,False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="查询新闻失败")

    # 4.获取分页对象属性,总页数,当前页,当前页对象
    totalPage= paginate.pages
    currentPage = paginate.page
    items = paginate.items

    # 5.对象列表转成字典列表
    news_list = []
    for item in items:
        news_list.append(item.to_review_dict())

    # 6.拼接数据,渲染页面
    data = {
        "totalPage":totalPage,
        "currentPage":currentPage,
        "news_list":news_list
    }
    return render_template('admin/news_edit.html',data=data)


# 新闻审核,详情
# 请求路径: /admin/news_review_detail
# 请求方式: GET,POST
# 请求参数: GET, news_id, POST,news_id, action
# 返回值:GET,渲染news_review_detail.html页面,data字典数据
@admin_blu.route('/news_review_detail', methods=['GET', 'POST'])
def news_review_detail():
    """
    思路分析:
    1.如果第一次进来是GEt请求
    2.获取到新闻编号查询新闻对象
    3.渲染到页面展示,携带新闻数据

    如果是第二次,证明是修改新闻状态
    1.获取参数
    2.校验参数,为空校验,操作类型校验
    3.根据新闻编号获取新闻对象
    4.判断新闻是否存在
    5.根据操作类型修改新闻状态
    6.返回响应
    :return:
    """
    # 1.如果第一次进来是GEt请求
    if request.method == 'GET':

        # 2.获取到新闻编号查询新闻对象
        news_id = request.args.get("news_id")

        #2.1判断编号是否存在
        if not news_id:
            return jsonify(errno=RET.PARAMERR,errmsg="新闻编号为空")

        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="获取新闻失败")

        if not news:
            return jsonify(errno=RET.NODATA,errmsg="新闻不存在")

        # 3.渲染到页面展示,携带新闻数据
        return render_template('admin/news_review_detail.html',news=news.to_dict())

    # 如果是第二次,证明是修改新闻状态
    # 1.获取参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 2.校验参数,为空校验,操作类型校验
    if not all([news_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不全")

    if not action in ["accept",'reject']:
        return jsonify(errno=RET.DATAERR,errmsg="操作类型有误")

    # 3.根据新闻编号获取新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取新闻失败")

    # 4.判断新闻是否存在
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 5.根据操作类型修改新闻状态
    if action == "accept":
        news.status = 0
    else:
        reason = request.json.get('reason')
        if not reason: return jsonify(errno=RET.DATAERR,errmsg="没有拒绝原因")
        news.status = -1
        news.reason = reason

    # 6.返回响应
    return jsonify(errno=RET.OK,errmsg="操作成功")

# 新闻审核列表
# 请求路径: /admin/news_review
# 请求方式: GET
# 请求参数: GET, p,keyword
# 返回值:渲染user_list.html页面,data字典数据
@admin_blu.route('/news_review')
def news_review():
    """
    思路分析:
    1.获取参数
    2.参数类型转换
    3.分页查询
    4.获取分页对象属性,总页数,当前页,当前页对象
    5.对象列表转成字典列表
    6.拼接数据,渲染页面
    :return:
    """
    # 1.获取参数
    page = request.args.get('p',1)
    keyword = request.args.get("keyword")

    # 2.参数类型转换
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 3.分页查询
    try:

        #判断是否有搜索关键字
        filters = [News.status != 0]
        if keyword:
            filters.append(News.title.contains(keyword))

        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,10,False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="查询新闻失败")

    # 4.获取分页对象属性,总页数,当前页,当前页对象
    totalPage= paginate.pages
    currentPage = paginate.page
    items = paginate.items

    # 5.对象列表转成字典列表
    news_list = []
    for item in items:
        news_list.append(item.to_review_dict())

    # 6.拼接数据,渲染页面
    data = {
        "totalPage":totalPage,
        "currentPage":currentPage,
        "news_list":news_list
    }
    return render_template('admin/news_review.html',data=data)


# 用户列表人数统计
# 请求路径: /admin/user_list
# 请求方式: GET
# 请求参数: p
# 返回值:渲染user_list.html页面,data字典数据
@admin_blu.route('/user_list')
def user_list():
    """
      思路分析 :
      1.获取参数
      2.参数类型转换
      3.分页获取作者新闻列表
      4.获取到分页对象属性,总页数,当前页,当前页对象
      5.返回响应,携带数据
      :return:
      """
    # 1.获取参数
    page = request.args.get('p', 1)

    # 2.参数类型转换
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 3.分页获取作者新闻列表
    try:
        paginate = User.query.order_by(User.create_time.desc()).paginate(page,10,False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻失败")

    # 4.获取到分页对象属性,总页数,当前页,当前页对象
    totalPage = paginate.pages
    currentPage = paginate.page
    items = paginate.items

    user_list = []
    for item in items:
        user_list.append(item.to_admin_dict())

    # 5.返回响应,携带数据
    data = {
        "totalPage": totalPage,
        "currentPage": currentPage,
        "user_list": user_list
    }
    return render_template('admin/user_list.html',data=data)


# 用户统计
# 请求路径: /admin/user_count
# 请求方式: GET
# 请求参数: 无
# 返回值:渲染页面user_count.html,字典数据
@admin_blu.route('/user_count')
def user_count():
    """
    思路分析:
    1.查询所有用户人数
    2.查询月活人数
    3.查询日活人数
    4.查询获取日期段
    5.查询获取日期段,所对应的活跃人数
    6.拼接数据渲染页面
    :return:
    """
    # 1.查询所有用户人数
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="获取总人数异常")
    
    # 2.查询月活人数
    # 获取日历对象
    cal = time.localtime()
    try:

        #创建本月1号的,时间字符串
        month_start_str = "%d-%d-01"%(cal.tm_year,cal.tm_mon)

        #创建本月1号的,时间对象
        month_start_date = datetime.datetime.strptime(month_start_str,"%Y-%m-%d")

        # 查询数据库
        month_count = User.query.filter(User.last_login >= month_start_date, User.is_admin == False).count()

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="获取月活人数异常")
    
    # 3.查询日活人数
    try:

        #创建本日,0点,时间字符串
        day_start_str = "%d-%d-%d"%(cal.tm_year,cal.tm_mon,cal.tm_mday)

        #创建本日,0点,时间对象
        day_start_date = datetime.datetime.strptime(day_start_str,"%Y-%m-%d")

        # 查询数据库
        day_count = User.query.filter(User.last_login >= day_start_date, User.is_admin == False).count()

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="获取月活人数异常")

    # 4.查询获取日期段
    # 5.查询获取日期段,所对应的活跃人数
    active_date = [] #活跃日期
    active_count = [] #活跃人数
    for i in range(0, 31):
        # 当天开始时间A
        begin_date = day_start_date - datetime.timedelta(days=i)
        # 当天开始时间, 的后一天B
        end_date = day_start_date - datetime.timedelta(days=i - 1)

        # 添加当天开始时间字符串到, 活跃日期中
        active_date.append(begin_date.strftime("%Y-%m-%d"))

        # 查询时间A到B这一天的注册人数
        everyday_active_count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                                  User.last_login <= end_date).count()

        # 添加当天注册人数到,获取数量中
        active_count.append(everyday_active_count)

    #为了方便查看图表,反转容器
    active_count.reverse()
    active_date.reverse()

    # 6.拼接数据渲染页面
    data = {
        "total_count":total_count,
        "month_count":month_count,
        "day_count":day_count,
        "active_date":active_date,
        "active_count":active_count
    }
    return render_template('admin/user_count.html',data=data)


# 管理员首页
# 请求路径: /admin/index
# 请求方式: GET
# 请求参数: 无
# 返回值:渲染页面index.html,user字典数据
@admin_blu.route('/index')
@user_login_data
def admin_index():

    data = {
        "user_info":g.user.to_dict() if g.user else ""
    }
    return render_template('admin/index.html',data=data)

# 管理员登陆页面
# 请求路径: /admin/login
# 请求方式: GET,POST
# 请求参数:GET,无, POST,username,password
# 返回值: GET渲染login.html页面, POST,login.html页面,errmsg
@admin_blu.route('/login', methods=['GET', 'POST'])
def admin_login():
    """
    思路分析:
    1.如果是第一次进来,渲染页面
    2.如果是第二次POSt,获取参数
    3.校验参数
    4.获取管理员用户对象
    5.判断密码是否正确
    6.记录session信息
    7.返回(重定向到首页)
    :return:
    """
    # 1.如果是第一次进来,渲染页面
    if request.method == 'GET':

        #判断是否已经登陆
        if session.get('is_admin'):
            return redirect(url_for('admin.admin_index'))

        return render_template('admin/login.html')

    # 2.如果是第二次POSt,获取参数
    username = request.form.get('username')
    password = request.form.get('password')

    # 3.校验参数
    if not all([username,password]):
        return render_template('admin/login.html',errmsg='参数不全')

    # 4.获取管理员用户对象
    try:
        user = User.query.filter(User.mobile == username,User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template('admin/login.html',errmsg="查询用户异常")

    if not user:
        return render_template('admin/login.html',errmsg="管理员不存在")

    # 5.判断密码是否正确
    if not user.check_passowrd(password):
        return render_template('admin/login.html',errmsg="密码不正确")

    # 6.记录session信息
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = user.is_admin

    # 7.返回(重定向到首页)
    # return redirect('/admin/index')
    return redirect(url_for('admin.admin_index'))