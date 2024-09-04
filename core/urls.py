# comments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('oauth/', views.google_oauth, name='google_oauth'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    path('select_channel/', views.select_channel, name='select_channel'),
    path('select_video/', views.select_video, name='select_video'),
    path('gather_insights/', views.gather_insights, name='gather_insights'),
    path('process_comments/', views.process_comments, name='process_comments'),
    path('success/', views.success, name='success'),
]
