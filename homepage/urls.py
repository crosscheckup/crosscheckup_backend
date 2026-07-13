from django.urls import path

from . import views

urlpatterns = [
    path('book-inspection/', views.BookInspectionView.as_view(), name='book-inspection'),
]
