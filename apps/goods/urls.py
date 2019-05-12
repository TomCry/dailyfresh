__author__ = 'enzyme'
__date__ = '2019/5/10 8:36 AM'

from django.conf.urls import url
from apps.goods import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
]
