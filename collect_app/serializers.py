from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Collect, Payment

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class PaymentSerializer(serializers.ModelSerializer):
    """Сериализатор для модели платежа."""
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    collect = serializers.PrimaryKeyRelatedField(queryset=Collect.objects.all())

    class Meta:
        model = Payment
        fields = ['id', 'collect', 'user', 'amount', 'created_at']
        read_only_fields = ['user', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class CollectSerializer(serializers.ModelSerializer):
    """Сериализатор для модели сбора."""
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    get_raised_percentage = serializers.IntegerField(read_only=True)
    get_full_occasion_display = serializers.CharField(read_only=True)

    class Meta:
        model = Collect
        fields = [
            'id', 'title', 'author', 'occasion', 'occasion_other_text', 'description',
            'goal_amount', 'raised_amount', # <-- Убедись, что здесь `raised_amount`
            'cover_image', 'end_at',
            'created_at', 'is_active', 'get_raised_percentage', 'get_full_occasion_display'
        ]
        read_only_fields = ['author', 'raised_amount', 'created_at']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)