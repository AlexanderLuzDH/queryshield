from django.http import JsonResponse
from .models import Book


def books_view(request):
    # Intentional N+1: accessing author in a loop without select_related
    data = []
    for b in Book.objects.all():
        data.append({"id": b.id, "title": b.title, "author": b.author.name})
    return JsonResponse({"books": data})


def books_view_opt(request):
    # Optimized: select_related to avoid N+1
    data = []
    for b in Book.objects.select_related("author").all():
        data.append({"id": b.id, "title": b.title, "author": b.author.name})
    return JsonResponse({"books": data})
