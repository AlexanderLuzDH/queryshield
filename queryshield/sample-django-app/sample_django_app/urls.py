from django.urls import path
from app.views import books_view, books_view_opt

urlpatterns = [
    path("books", books_view),
    path("books_opt", books_view_opt),
]
