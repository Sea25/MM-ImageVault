from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('preview/', views.preview_image, name='preview_image'),
    path('delete/<int:id>/', views.delete_image, name='delete_image'),
]
