from django.contrib.auth import authenticate
from rest_framework import serializers


from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .models import ProductInfo, ProductParameter, OrderItem, Order, Contact

User = get_user_model()


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=5)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            username=validated_data['email'],
            is_active=True,
            type='buyer',
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs['email'],
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError('Неверный email или пароль')
        if not user.is_active:
            raise serializers.ValidationError('Пользователь не активен')
        attrs['user'] = user
        return attrs
    
class ProductParameterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='parameter.name')

    class Meta:
        model = ProductParameter
        fields = ('name', 'value')


class ProductInfoSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='product.name')
    description = serializers.CharField(source='model')
    shop = serializers.CharField(source='shop.name')
    parameters = ProductParameterSerializer(source='product_parameters', many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'name', 'description', 'shop', 'parameters', 'price', 'quantity')


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source='product_info.product.name')
    shop = serializers.CharField(source='product_info.shop.name')
    price = serializers.IntegerField(source='product_info.price')
    total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'shop', 'price', 'quantity', 'total')

    def get_total(self, obj):
        return obj.quantity * obj.product_info.price


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='ordered_items', many=True)
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'items', 'total_sum')

    def get_total_sum(self, obj):
        return sum(
            item.quantity * item.product_info.price
            for item in obj.ordered_items.all()
        )
    
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'id',
            'city',
            'street',
            'house',
            'structure',
            'building',
            'apartment',
            'phone',
        )


class OrderListSerializer(serializers.ModelSerializer):
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'dt', 'state', 'total_sum')

    def get_total_sum(self, obj):
        return sum(
            item.quantity * item.product_info.price
            for item in obj.ordered_items.all()
        )
        