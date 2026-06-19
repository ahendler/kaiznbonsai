from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'email', 'password')

    def create(self, validated_data):
        email = validated_data['email']
        return User.objects.create_user(
            # username mirrors email — it's an internal detail, not exposed by the API
            username=email,
            email=email,
            password=validated_data['password'],
        )
