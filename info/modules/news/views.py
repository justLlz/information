from info import db
from info.models import User, News, Comment, CommentLike
from info.utils.commons import user_login_data
from info.utils.response_code import RET
from . import news_blu
from flask import render_template, session, current_app, g, jsonify, abort, request

# 关注/取消关注
# 请求路径: /news/followed_user
# 请求方式: POST
# 请求参数:user_id,action
# 返回值: errno, errmsg
@news_blu.route('/followed_user', methods=['POST'])
@user_login_data
def followed_user():
    """
    思路分析:
    0.判断用户是否登陆
    1.获取参数
    2.校验参数
    3.根据user_id取出作者对象
    4.判断作者对象是否存在
    5.根据操作类型,关注或者取关
    6.返回响应
    :return:
    """
    # 0.判断用户是否登陆
    if not g.user:
        return jsonify(errno=RET.NODATA,errmsg="用户未登录")

    # 1.获取参数
    author_id = request.json.get('user_id')
    action = request.json.get('action')

    # 2.校验参数
    if not all([author_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不全")

    if not action in ["follow","unfollow"]:
        return jsonify(errno=RET.DATAERR,errmsg="操作类型错误")

    # 3.根据user_id取出作者对象
    try:
        author = User.query.get(author_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="查询用户失败")

    # 4.判断作者对象是否存在
    if not author: return jsonify(errno=RET.NODATA,errmsg="作者不存在")

    # 5.根据操作类型,关注或者取关
    try:
        if action == 'follow':
            # 判断是否关注过作者了
            if not g.user in author.followers:
                author.followers.append(g.user)
        else:
            # 判断是否关注过作者了
            if g.user in author.followers:
                author.followers.remove(g.user)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="操作失败")


    # 6.返回响应
    return jsonify(errno=RET.OK,errmsg="操作成功")



#点赞,取消点赞
# 请求路径: /news/comment_like
# 请求方式: POST
# 请求参数:news_id[可选],comment_id,action,g.user
# 返回值: errno,errmsg
@news_blu.route('/comment_like', methods=['POST'])
@user_login_data
def comment_like():
    """
    思路分析:
    0.判断用户是否登陆
    1.获取参数
    2.校验参数
    3.通过评论编号获取评论对象
    4.判断评论对象是否存在
    5.根据操作类型,点赞/取消点赞
    6.更新数据库
    7.返回响应
    :return:
    """

    #0.判断用户是否登陆
    if not g.user:
        return jsonify(errno=RET.NODATA,errmsg="用户未登录")

    # 1.获取参数
    comment_id = request.json.get('comment_id')
    action = request.json.get('action')

    # 2.校验参数
    if not all([comment_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不全")

    if not action in ["add","remove"]:
        return jsonify(errno=RET.DATAERR,errmsg="操作类型有误")

    # 3.通过评论编号获取评论对象
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="查询失败")

    # 4.判断评论对象是否存在
    if not comment:
        return jsonify(errno=RET.NODATA,errmsg="评论不存在")

    # 5.根据操作类型,点赞/取消点赞
    if action == "add":
        #判断用户是否点过赞
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,CommentLike.user_id == g.user.id).first()
        if not comment_like:
            #创建点赞对象,设置属性
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = g.user.id

            db.session.add(comment_like)

            #点赞数量+1
            comment.like_count += 1
    else:
        # 判断用户是否点过赞
        comment_like = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                CommentLike.user_id == g.user.id).first()
        if  comment_like:
            #删除点赞
            db.session.delete(comment_like)

            # 点赞数量-1
            comment.like_count -= 1

    # 6.更新数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="操作失败")

    # 7.返回响应
    return jsonify(errno=RET.OK,errmsg="操作成功")


# 新闻评论
# 请求路径: /news/news_comment
# 请求方式: POST
# 请求参数:news_id,comment,parent_id
# 返回值: errno,errmsg,评论字典
@news_blu.route('/news_comment', methods=['POST'])
@user_login_data
def news_comment():
    """
    思路分析:
    0.判断用户是否存在
    1.获取参数
    2.校验参数
    3.通过新闻编号取出新闻对象
    4.判断新闻对象是否存在
    5.创建评论对象,设置属性
    6.保存评论到数据库
    7.返回响应
    :return:
    """

    #0. 判断用户是否存在
    if not g.user:
        return jsonify(errno=RET.NODATA,errmsg="用户未登录")

    # 1.获取参数
    news_id = request.json.get('news_id')
    content = request.json.get('comment')
    parent_id = request.json.get('parent_id')

    # 2.校验参数
    if not all([news_id,content]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不全")

    # 3.通过新闻编号取出新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="新闻查询失败")

    # 4.判断新闻对象是否存在
    if not news:
        return jsonify(errno=RET.NODATA,errmsg="新闻不存在")

    # 5.创建评论对象,设置属性
    comment = Comment()
    comment.user_id = g.user.id
    comment.news_id = news_id
    comment.content = content
    if parent_id:
        comment.parent_id = parent_id

    # 6.保存评论到数据库
    try:
        db.session.add(comment)
        db.session.commit() #提交及时
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="评论失败")

    # 7.返回响应
    return jsonify(errno=RET.OK,errmsg="评论成功",data=comment.to_dict())



# 新闻收藏/取消收藏
# 请求路径: /news/news_collect
# 请求方式: POST
# 请求参数:news_id,action, g.user
# 返回值: errno,errmsg
@news_blu.route('/news_collect', methods=['POST'])
@user_login_data
def news_collect():
    """
    思路分析:
    0.判断用户是否登陆
    1.获取参数
    2.校验参数,为空校验,action操作类型
    3.根据新闻编号获取新闻对象
    4.判断新闻是否存在
    5.根据操作类型,做收藏或者取消收藏操作
    6.返回响应即可
    :return:
    """
    
    #0. 判断用户是否登陆
    if not g.user:
        return jsonify(errno=RET.NODATA,errmsg="用户未登录")
    
    # 1.获取参数
    news_id = request.json.get('news_id')
    action = request.json.get('action')

    # 2.校验参数,为空校验,action操作类型
    if not all([news_id,action]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不全")

    if not action in ['collect','cancel_collect']:
        return jsonify(errno=RET.PARAMERR,errmsg="操作类型有误")

    # 3.根据新闻编号获取新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="新闻查询异常")
    
    # 4.判断新闻是否存在
    if not news:
        return jsonify(errno=RET.NODATA,errmsg="新闻不存在")
    
    # 5.根据操作类型,做收藏或者取消收藏操作
    if action == 'collect':
        #判断用户是否收藏该新闻
        if not news in g.user.collection_news:
            g.user.collection_news.append(news)
    else:
        #判断用户是否收藏该新闻
        if news in g.user.collection_news:
            g.user.collection_news.remove(news)
        
    #跟新数据库
    # try:
    #     db.session.commit()
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(errno=RET.DBERR,errmsg="操作失败")
    
    # 6.返回响应即可
    return jsonify(errno=RET.OK,errmsg="操作成功")



#新闻详情展示
# 请求路径: /news/<int:news_id>
# 请求方式: GET
# 请求参数:news_id
# 返回值: detail.html页面, 用户data字典数据
@news_blu.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):

    #根据新闻编号,获取新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="查询新闻失败")

    #判断新闻对象是否存在,(以后实现,统一处理404页面)
    if not news:
        abort(404)


    #查询热门新闻数据
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(8).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="获取新闻失败")

    #将新闻对象列表,转成字典列表
    click_news_list = []
    for item in news_list:
        click_news_list.append(item.to_dict())


    #判断用户对当前新闻是否有收藏
    is_collected = False
    #用户登陆,并且新闻在用户的收藏列表, 那么证明用户收藏了该新闻
    if g.user and news in g.user.collection_news:
        is_collected = True

    #查询当前新闻的所有评论
    try:
        comments = news.comments.order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="获取评论失败")

    my_like_comment_ids = []
    if g.user:
        try:
            #获取所有的评论编号
            comments_ids = [comm.id for comm in comments]

            #获取到登陆用户,的点赞对象
            comment_like_list = CommentLike.query.filter(CommentLike.comment_id.in_(comments_ids),CommentLike.user_id == g.user.id).all()

            #获取用户点赞过的comment_id
            my_like_comment_ids =  [comm_like.comment_id for comm_like in comment_like_list]
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="查询失败")

    #将所有评论遍历成字典
    comment_list = []
    for comment in comments:

        comment_dict = comment.to_dict()
        comment_dict['is_like'] = False
        # if 当前用户是否有登陆 and 评论编号在用户的点赞对象列表中:
        if g.user and comment.id in my_like_comment_ids:
            comment_dict['is_like'] = True

        comment_list.append(comment_dict)

    #判断当前用户有没有,关注过该新闻的作者
    is_followed = False
    if g.user and news.user:
        # 登陆的用户在作者的粉丝列表中
        if g.user in news.user.followers:
            is_followed = True

    data = {
        "user_info":g.user.to_dict() if g.user else "",
        "click_news_list":click_news_list,
        "news":news.to_dict(),
        "is_collected":is_collected,
        "comments":comment_list,
        "is_followed":is_followed
    }

    return render_template('news/detail.html',data=data)