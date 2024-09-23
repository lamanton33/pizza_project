# orders/views.py

from django.shortcuts import render, redirect
from .models import Pizza, Drink, Dessert, Order, OrderItem, DiscountCode
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def place_order(request):
    if request.method == 'POST':
        # Process order
        cart = request.session.get('cart', [])
        discount_code = request.POST.get('discount_code')
        order = Order.objects.create(customer=request.user.customer)
        
        for item in cart:
            OrderItem.objects.create(
                order=order,
                item_type=item['type'],
                item_id=item['id'],
                quantity=item['quantity']
            )
        
        if discount_code:
            try:
                discount = DiscountCode.objects.get(code=discount_code, is_redeemed=False)
                order.discount_applied = discount.discount_amount
                order.apply_discount()
            except DiscountCode.DoesNotExist:
                messages.error(request, "Invalid or already redeemed discount code.")
        
        order.assign_delivery_person()
        request.session['cart'] = []
        messages.success(request, "Order placed successfully!")
        return redirect('order_confirmation', order_id=order.id)
    
    return render(request, 'orders/place_order.html')

