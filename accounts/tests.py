from django.test import TestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from accounts.authentication import UnsafeUserAuthentication, UnsafeUserToken
from accounts.enums import UserRole
from accounts.models import ApiUser

HEADER = "X-Unsafe-User-Id"


class ApiUserTests(TestCase):
    def test_api_user_is_unique_by_unsafe_id(self) -> None:
        user, created = ApiUser.objects.get_or_create(unsafe_id=7)
        again, created_again = ApiUser.objects.get_or_create(unsafe_id=7)

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(again.pk, user.pk)
        self.assertEqual(user.role, UserRole.PASSING)
        self.assertEqual(ApiUser.objects.count(), 1)


class UnsafeUserAuthenticationTests(TestCase):
    def setUp(self) -> None:
        self.authentication = UnsafeUserAuthentication()
        self.factory = APIRequestFactory()

    def authenticate(
        self, value: str | None = None, header: str = HEADER
    ) -> tuple[ApiUser, UnsafeUserToken] | None:
        headers = {} if value is None else {header: value}
        return self.authentication.authenticate(self.factory.get("/", headers=headers))

    def test_header_creates_api_user_once(self) -> None:
        authenticated = self.authenticate("12345")

        assert authenticated is not None
        user, token = authenticated
        self.assertEqual(user.unsafe_id, 12345)
        self.assertEqual(token, UnsafeUserToken(unsafe_id=12345))
        self.assertTrue(user.is_authenticated)
        self.assertFalse(user.is_anonymous)

        repeated = self.authenticate("12345")

        assert repeated is not None
        self.assertEqual(repeated[0].pk, user.pk)
        self.assertEqual(ApiUser.objects.count(), 1)

    def test_missing_or_invalid_header_is_rejected(self) -> None:
        self.assertIsNone(self.authenticate())

        for value in ("", " ", "abc", "-1", "0", "1.5", "1e3", "привет", "1" * 25, "1" * 5000):
            with self.subTest(value=value), self.assertRaises(AuthenticationFailed):
                self.authenticate(value)

        self.assertEqual(ApiUser.objects.count(), 0)

    @override_settings(UNSAFE_USER_AUTO_CREATE=False)
    def test_unknown_user_is_rejected_without_auto_create(self) -> None:
        with self.assertRaises(AuthenticationFailed):
            self.authenticate("7")

        self.assertEqual(ApiUser.objects.count(), 0)

        user = ApiUser.objects.create(unsafe_id=7)
        authenticated = self.authenticate("7")

        assert authenticated is not None
        self.assertEqual(authenticated[0].pk, user.pk)
