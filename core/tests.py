import uuid

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.urls import resolve
from ulid import ULID

from core.models import ULIDField, new_ulid


class ApplicationTests(TestCase):
    def test_system_checks_pass(self) -> None:
        self.assertEqual(call_command("check"), None)

    def test_urlconf_loads(self) -> None:
        self.assertIsNotNone(resolve("/admin/").func)

    def test_database_connection_works(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone(), (1,))


class ULIDFieldTests(TestCase):
    def setUp(self) -> None:
        self.field = ULIDField()
        self.value = new_ulid()
        self.ulid = ULID.from_uuid(self.value)

    def test_accepts_supported_representations(self) -> None:
        representations = (self.ulid, str(self.ulid), self.value, str(self.value), self.value.hex)

        for representation in representations:
            with self.subTest(representation=representation):
                self.assertEqual(self.field.to_python(representation), self.value)

        self.assertEqual(self.field.get_prep_value(self.ulid), self.field.get_prep_value(self.value))

    def test_blank_becomes_none_and_invalid_raises(self) -> None:
        for value in (None, "", "   "):
            with self.subTest(value=value):
                self.assertIsNone(self.field.to_python(value))

        self.assertEqual(self.field.to_python("0" * 26), uuid.UUID(int=0))

        for invalid in ("not-a-ulid", "I" * 26, "0" * 27, 12345):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                self.field.to_python(invalid)
