from django.test import TestCase
from app.models import Author, Book


class NPlusOneTest(TestCase):
    def setUp(self):
        a = Author.objects.create(name="A")
        for i in range(10):
            Book.objects.create(title=f"B{i}", author=a)

    def test_books_view_nplus1(self):
        # Import here to avoid circular import issues
        from django.test import Client

        client = Client()
        resp = client.get("/books")
        assert resp.status_code == 200

    def test_books_view_optimized(self):
        from django.test import Client

        client = Client()
        resp = client.get("/books_opt")
        assert resp.status_code == 200
