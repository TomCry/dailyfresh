from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.http import HttpResponse
from django.conf import settings
from apps.user.models import User
from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired

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
        return render(request, 'login.html')
