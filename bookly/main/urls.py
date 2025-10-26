from django.urls import path
from . import views

urlpatterns = [
    path('', views.text),
    path('admin', views.first)

]
