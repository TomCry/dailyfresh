__author__ = 'enzyme'
__date__ = '2019/5/10 8:36 AM'

from django.conf.urls import url
from user.views import RegisterView, ActiveView, LoginView

urlpatterns = [
    # url(r'^register/$', views.register, name='register'),
    # url(r'^register_handler/$', views.register_handler, name='register_handler'),
    url(r'^register/$', RegisterView.as_view(), name='register'),
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    url(r'^login/$', LoginView.as_view(), name='login'),
]
