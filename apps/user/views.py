from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout
from django.views.generic import View
from django.http import HttpResponse
from django.conf import settings
from apps.user.models import User, Address
from apps.goods.models import GoodsSKU
from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from utils.minxi import LoginRequiredMixin
from django_redis import get_redis_connection

import re


# Create your views here.
# def register(request):
#     """显示注册页面"""
#     if request.method == 'GET':
#         return render(request, 'register.html')
#     else:
#         # 接收register页面提交的数据
#         username = request.POST.get('user_name')
#         password = request.POST.get('pwd')
#         email = request.POST.get('email')
#         allow = request.POST.get('allow')
#
#         # 业务校验
#
#         if not all([username, password, email]):
#             # 数据不完整
#             return render(request, 'register.html', {'errmsg': '数据不完整'})
#         # 密码校验，校验是否符合字母，数字，符号，第一个字母必须以大写字母开头
#
#         # email校验，校验邮箱是否符合邮箱格式，正则匹配
#         if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
#             return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
#         # 校验是否同意协议
#         if allow != 'on':
#             return render(request, 'register.html', {'errmsg': '请同意协议！'})
#
#         # username校验，校验是否存在，如果存在，则返回当前页面，并alert提示错误信息
#         try:
#             user = User.objects.get(username=username)
#         except User.DoesNotExist:
#             # 用户名不存在
#             user = None
#
#         if user:
#             return render(request, 'register.html', {'errmsg': '用户名已存在'})
#         # 如果校验通过，则创建用户，否则返回异常信息至前端页面显示（alert）
#         user = User.objects.create_user(username, email, password)
#         # 创建用户保持新用户未激活
#         user.is_active = 0
#         user.save()
#         # 最后返回到index.html页面并提示用户注册成功
#         return redirect(reverse('goods:index'))


# def register_handler(request):

class RegisterView(View):
    """注册"""

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 业务校验

        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 密码校验，校验是否符合字母，数字，符号，第一个字母必须以大写字母开头

        # email校验，校验邮箱是否符合邮箱格式，正则匹配
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
        # 校验是否同意协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议！'})

        # username校验，校验是否存在，如果存在，则返回当前页面，并alert提示错误信息
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 如果校验通过，则创建用户，否则返回异常信息至前端页面显示（alert）
        user = User.objects.create_user(username, email, password)
        # 创建用户保持新用户未激活
        user.is_active = 0
        user.save()

        # 加密信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        # 取消链接后的b
        token = token.decode()
        # 发邮件
        send_register_active_email.delay(email, username, token)
        # 最后返回到index.html页面并提示用户注册成功
        return redirect(reverse('goods:index'))


class ActiveView(View):
    """用户激活验证"""

    def get(self, request, token):
        """进行用户激活"""
        # 解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']
            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 用户已激活，跳转到登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired:
            # 激活链接过期
            return HttpResponse('激活链接已过期')


# /user/login
class LoginView(View):

    def get(self, request):
        # 判断是否记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)
                # 判断是否需要记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')

                return response

            else:
                return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class LogoutView(View):

    def get(self, request):
        # 清除用户的session信息
        logout(request)

        return redirect(reverse('goods:index'))


# /user
class UserInfoView(LoginRequiredMixin, View):

    def get(self, request):
        # 除了你给模板文件传递的模板变量之外， jango框架会把request.user也传给模板文件
        # 如果用户登录则是user类的一个实例，否则是一个AnonymousUser的实例
        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取用户的个人历史浏览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host='192.168.33.239', port='6379', db=9)
        con = get_redis_connection('default')
        history_key = 'history_%d' % user.id
        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)

        # 从数据库中查询用户浏览商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)

        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)
        # 遍历获取用户浏览的历史商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {
            'page': 'user',
            'address': address,
            'goods_li': goods_li
        }

        return render(request, 'user_center_info.html', context)


class UserOrderView(LoginRequiredMixin, View):

    def get(self, request):
        # 获取用户的订单信息

        return render(request, 'user_center_order.html', {'page': 'order'})


class AddressView(LoginRequiredMixin, View):

    def get(self, request):
        """显示"""
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取用户的默认收货地址

        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        """地址的添加"""
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        # 校验传入数据完整性，zip_code在数据库设计的时候字段可以为空
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})
        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8|9][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机格式不正确'})

        # 业务处理：地址添加
        # 如果用户已存在默认的收货的地址，添加的地址不作为默认收货地址，否则作为默认收货地址
        # 获取已登录用户的对象
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(
            user=user,
            receiver=receiver,
            addr=addr,
            zip_code=zip_code,
            phone=phone,
            is_default=is_default
        )

        # 返回应答,刷新地址页面
        return redirect(reverse('user:address'))
