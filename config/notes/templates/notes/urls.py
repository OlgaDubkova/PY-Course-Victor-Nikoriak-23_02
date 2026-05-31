from django.urls import path
from . import views

urlpatterns = [
    path('', views.note_create, name='note_create'),
    path('<int:pk>/', views.note_detail_edit, name='note_detail_edit'),
    path('<int:pk>/delete/', views.note_delete, name='note_delete'),
]