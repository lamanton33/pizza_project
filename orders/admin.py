from django.contrib import admin
from .models import Customer, Pizza, Drink, Dessert, Order, OrderItem, DeliveryPerson, PostalCode, DiscountCode, Ingredient

admin.site.register(Customer)
admin.site.register(Pizza)
admin.site.register(Drink)
admin.site.register(Dessert)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(DeliveryPerson)
admin.site.register(PostalCode)
admin.site.register(DiscountCode)
admin.site.register(Ingredient)
