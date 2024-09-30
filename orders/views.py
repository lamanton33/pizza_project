from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Customer, Pizza, Drink, Dessert, Order, OrderItem, DiscountCode, EarningsReport, PostalCode
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta


# Customer Registration View

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        birthdate = request.POST.get('birthdate')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        postal_code_id = request.POST.get('postal_code')
        gender = request.POST.get('gender')
    
        # Check parola
        if password != password_confirm:
            messages.error(request, "Пароли не совпадают.")
            return redirect('register')
    
        # Check user
        if User.objects.filter(username=username).exists():
            messages.error(request, "Пользователь с таким именем уже существует.")
            return redirect('register')
    
        
        user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
    
        
        try:
            postal_code = PostalCode.objects.get(id=postal_code_id)
        except PostalCode.DoesNotExist:
            messages.error(request, "Выбранный почтовый код не существует.")
            user.delete()
            return redirect('register')
    

        Customer.objects.create(
            user=user,
            birthdate=birthdate,
            phone_number=phone_number,
            address=address,
            postal_code=postal_code,
            gender=gender,
            total_pizzas_ordered=0,
            birthday_reward_redeemed=False
        )
    
        messages.success(request, "Регистрация прошла успешно. Вы можете войти в систему.")
        return redirect('login')  
    

    postal_codes = PostalCode.objects.all()
    return render(request, 'orders/register.html', {'postal_codes': postal_codes})

# Customer Login View
def user_login(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user:
            login(request, user)
            return redirect('place_order')
        else:
            messages.error(request, 'Invalid login credentials')
    return render(request, 'orders/login.html')

# Customer Logout View
@login_required
def user_logout(request):
    logout(request)
    return redirect('orders/login.html')

# Order Placement View
@login_required
def place_order(request):
    if request.method == 'POST':
        order = Order.objects.create(customer=request.user.customer)
        
        # Add pizzas
        pizza_ids = request.POST.getlist('pizzas')
        #add logic if no pizza then pashel nahui and need to add at least 1 pizza for order
        for pizza_id in pizza_ids:
            pizza = get_object_or_404(Pizza, id=pizza_id)
            OrderItem.objects.create(
                order=order,
                content_type=ContentType.objects.get_for_model(pizza),
                object_id=pizza.id,
                quantity=1
            )
            # Update the customer's total pizzas ordered
            request.user.customer.total_pizzas_ordered += 1
            request.user.customer.save()
        
        # Add drinks
        drink_ids = request.POST.getlist('drinks')
        for drink_id in drink_ids:
            drink = get_object_or_404(Drink, id=drink_id)
            OrderItem.objects.create(
                order=order,
                content_type=ContentType.objects.get_for_model(drink),
                object_id=drink.id,
                quantity=1
            )

        # Add desserts
        dessert_ids = request.POST.getlist('desserts')
        for dessert_id in dessert_ids:
            dessert = get_object_or_404(Dessert, id=dessert_id)
            OrderItem.objects.create(
                order=order,
                content_type=ContentType.objects.get_for_model(dessert),
                object_id=dessert.id,
                quantity=1
            )

        # Apply discount if a valid discount code is provided
        discount_code = request.POST.get('discount_code')
        if discount_code:
            try:
                code = DiscountCode.objects.get(code=discount_code, is_redeemed=False)
                if code.customer == request.user.customer or code.customer is None:
                    order.discount_code = code
                    order.save()
                else:
                    messages.error(request, 'Invalid discount code for your account.')
                    return redirect('place_order')
            except DiscountCode.DoesNotExist:
                messages.error(request, 'Invalid discount code.')
                return redirect('place_order')

        # Apply all discounts (loyalty, birthday, and discount code)

        try:
            order.clean()  # Validate order
            order.assign_delivery_person() # Try to assing delivery person
            order.apply_discount()
        except ValidationError as e:
            messages.error(request, e.message)
            order.delete()  # Delete wrong order
            return redirect('place_order')    

        order.apply_discount()
        messages.success(request, f"Order placed successfully! Your total is {order.get_total_price()}. Estimated delivery time: {order.estimated_delivery_time}")    
        return redirect('order_confirmation', order_id=order.id)

    pizzas = Pizza.objects.all()
    drinks = Drink.objects.all()
    desserts = Dessert.objects.all()
    return render(request, 'orders/place_order.html', {'pizzas': pizzas, 'drinks': drinks, 'desserts': desserts})

# Order Confirmation View
@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user.customer)
    context = {'order': order, 'total_price': order.get_total_price()}
    return render(request, 'orders/order_confirmation.html', context)

# Order History View
@login_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user.customer).order_by('-date')
    return render(request, 'orders/order_history.html', {'orders': orders})

# Cancel Order View
@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user.customer)
    if order.can_cancel():
        order.cancel_order()
        messages.success(request, 'Order has been canceled successfully.')
    else:
        messages.error(request, 'You can no longer cancel this order.')
    return redirect('order_history')

# Restaurant Monitoring View (Staff-only view)
@login_required
def restaurant_monitoring(request):
    if not request.user.is_staff:
        return HttpResponse('Unauthorized', status=401)
    orders = Order.objects.filter(status__in=['P', 'I', 'O']).order_by('-date')
    return render(request, 'orders/restaurant_monitoring.html', {'orders': orders})

# Earnings Report View (Staff-only view)
@login_required
def earnings_report(request):
    if not request.user.is_staff:
        return HttpResponse('Unauthorized', status=401)
    reports = EarningsReport.objects.all()
    return render(request, 'orders/earnings_report.html', {'reports': reports})

def home(request):
    return render(request, 'orders/home.html')  
