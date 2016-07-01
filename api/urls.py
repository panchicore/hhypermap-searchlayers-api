from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from api import views

urlpatterns = [
    url(r'^tweets/search/$', views.TweetsSearch.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)