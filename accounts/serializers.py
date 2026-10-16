from rest_framework import serializers

from accounts.models import ApiUser


class ApiUserSerializer(serializers.ModelSerializer[ApiUser]):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = ApiUser
        fields = ["id", "unsafe_id", "role", "role_display"]
        read_only_fields = ["id", "unsafe_id", "role", "role_display"]
