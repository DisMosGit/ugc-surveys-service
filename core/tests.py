
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.urls import resolve


class ApplicationTests(TestCase):
    def test_system_checks_pass(self) -> None:
        self.assertEqual(call_command("check"), None)

    def test_urlconf_loads(self) -> None:
        self.assertIsNotNone(resolve("/admin/").func)

    def test_database_connection_works(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone(), (1,))
