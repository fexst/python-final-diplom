from django.urls import path
from .views import (PartnerUpdate, RegisterUserAPIView, LoginAPIView, ProductInfoListAPIView,  
                    BasketAPIView, BasketAddAPIView, BasketDeleteAPIView, ContactAPIView,
                    ContactCreateAPIView, ContactDeleteAPIView, OrderConfirmAPIView, OrderListAPIView)


urlpatterns = [
    path('user/register/', RegisterUserAPIView.as_view()),
    path('user/login/', LoginAPIView.as_view()),
    path('partner/update/', PartnerUpdate.as_view()),
    path('products/', ProductInfoListAPIView.as_view()),
    path('basket/', BasketAPIView.as_view()),
    path('basket/add/', BasketAddAPIView.as_view()),
    path('basket/delete/', BasketDeleteAPIView.as_view()),
    path('contacts/', ContactAPIView.as_view()),
    path('contacts/create/', ContactCreateAPIView.as_view()),
    path('contacts/delete/', ContactDeleteAPIView.as_view()),
    path('order/confirm/', OrderConfirmAPIView.as_view()),
    path('orders/', OrderListAPIView.as_view()),
]
