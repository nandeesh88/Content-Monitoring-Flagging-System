from django.urls import path
from . import views

urlpatterns = [
    path('keywords/', views.create_keyword, name='create-keyword'),
    path('keywords/list/', views.list_keywords, name='list-keywords'),
    path('scan/', views.trigger_scan, name='trigger-scan'),
    path('flags/', views.list_flags, name='list-flags'),
    path('flags/<int:pk>/', views.update_flag, name='update-flag'),
]
