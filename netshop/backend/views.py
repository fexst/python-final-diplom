from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.http import JsonResponse
from requests import get, RequestException
from rest_framework.views import APIView
from yaml import safe_load
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import (RegisterUserSerializer, LoginSerializer, ProductInfoSerializer, 
                          OrderSerializer, ContactSerializer, OrderListSerializer)

from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact
from django.db.models import Q
from rest_framework.generics import ListAPIView








class PartnerUpdate(APIView):
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if not url:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': str(e)}, status=400)

        try:
            response = get(url, timeout=10)
            response.raise_for_status()
        except RequestException as e:
            return JsonResponse({'Status': False, 'Error': str(e)}, status=400)

        try:
            data = safe_load(response.content)
        except Exception as e:
            return JsonResponse({'Status': False, 'Error': f'Ошибка чтения YAML: {e}'}, status=400)

        try:
            with transaction.atomic():
                shop, _ = Shop.objects.get_or_create(
                    name=data['shop'],
                    user=request.user
                )

                category_map = {}

                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(
                        name=category['name']
                    )
                    category_object.shops.add(shop)
                    category_map[category['id']] = category_object

                ProductInfo.objects.filter(shop=shop).delete()

                for item in data['goods']:
                    category_object = category_map[item['category']]

                    product, _ = Product.objects.get_or_create(
                        name=item['name'],
                        category=category_object
                    )

                    product_info = ProductInfo.objects.create(
                        product=product,
                        external_id=item['id'],
                        model=item['model'],
                        price=item['price'],
                        price_rrc=item['price_rrc'],
                        quantity=item['quantity'],
                        shop=shop
                    )

                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(
                            product_info=product_info,
                            parameter=parameter_object,
                            value=str(value)
                        )

        except Exception as e:
            return JsonResponse({'Status': False, 'Error': str(e)}, status=400)

        return JsonResponse({'Status': True})


class RegisterUserAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'Status': True,
            'Token': token.key,
            'User_id': user.id,
        })


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'Status': True,
            'Token': token.key,
            'User_id': user.id,
        })

 
class ProductInfoListAPIView(ListAPIView):
    serializer_class = ProductInfoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = ProductInfo.objects.select_related(
            'product', 'shop'
        ).prefetch_related(
            'product_parameters__parameter'
        ).filter(
            shop__state=True
        )

        query = self.request.query_params.get('query')
        shop_id = self.request.query_params.get('shop_id')
        category_id = self.request.query_params.get('category_id')

        if query:
            queryset = queryset.filter(
                Q(product__name__icontains=query) |
                Q(model__icontains=query) |
                Q(product__category__name__icontains=query)
            )

        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)

        if category_id:
            queryset = queryset.filter(product__category_id=category_id)

        return queryset
    

class BasketAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        order, _ = Order.objects.get_or_create(
            user=request.user,
            state='basket'
        )
        return Response(OrderSerializer(order).data)
    

class BasketAddAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        product_info_id = request.data.get('product_info_id')
        quantity = request.data.get('quantity', 1)

        if not product_info_id:
            return Response({'error': 'product_info_id required'}, status=400)

        product_info = ProductInfo.objects.filter(id=product_info_id).first()
        if not product_info:
            return Response({'error': 'Product not found'}, status=404)

        order, _ = Order.objects.get_or_create(
            user=request.user,
            state='basket'
        )

        item, created = OrderItem.objects.get_or_create(
            order=order,
            product_info=product_info,
            defaults={'quantity': quantity}
        )

        if not created:
            item.quantity += int(quantity)
            item.save()

        return Response({'Status': True})
    

class BasketDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        item_id = request.data.get('item_id')

        if not item_id:
            return Response({'error': 'item_id required'}, status=400)

        item = OrderItem.objects.filter(
            id=item_id,
            order__user=request.user,
            order__state='basket'
        ).first()

        if not item:
            return Response({'error': 'Item not found'}, status=404)

        item.delete()
        return Response({'Status': True})
    

class ContactAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        return Response(ContactSerializer(contacts, many=True).data)
    

class ContactCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response({'Status': True})

class ContactDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        contact_id = request.data.get('contact_id')

        contact = Contact.objects.filter(
            id=contact_id,
            user=request.user
        ).first()

        if not contact:
            return Response({'error': 'Contact not found'}, status=404)

        contact.delete()
        return Response({'Status': True})
    

class OrderConfirmAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        contact_id = request.data.get('contact_id')

        order = Order.objects.filter(
            user=request.user,
            state='basket'
        ).first()

        if not order:
            return Response({'error': 'Basket not found'}, status=404)

        if not order.ordered_items.exists():
            return Response({'error': 'Basket is empty'}, status=400)

        contact = Contact.objects.filter(
            id=contact_id,
            user=request.user
        ).first()

        if not contact:
            return Response({'error': 'Contact not found'}, status=404)

        order.contact = contact
        order.state = 'new'
        order.save()

        return Response({'Status': True})
    

class OrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).exclude(state='basket')

        return Response(OrderListSerializer(orders, many=True).data)
