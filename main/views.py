from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count
from django.db import transaction
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from .forms import SignUpForm, FoodForm
from .models import User, Shop, Food, Order, COURIERS
from decimal import Decimal
from datetime import timedelta
import random

def _require_business(request):
    if not request.user.is_authenticated or not request.user.is_business():
        raise PermissionDenied

def home(request):
    return render(request, "home.html")

def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = form.cleaned_data["role"]
            user.save()

            if user.role == User.BUSINESS:
                Shop.objects.create(
                    owner=user,
                    name=form.cleaned_data["shop_name"],
                    address=form.cleaned_data["shop_address"],
                    cuisine=form.cleaned_data["shop_cuisine"],
                )

            login(request, user)

            if user.role == User.BUSINESS:
                messages.success(
                    request,
                    f"Welcome to Tazaj, {user.username}! Your shop is ready.",
                )
            else:
                messages.success(request, f"Welcome to Tazaj, {user.username}!")

            return redirect("home")
    else:
        form = SignUpForm()

    return render(request, "signup.html", {"form": form})

def browse(request):
    foods = (
        Food.objects
        .filter(is_active=True, shop__is_active=True)
        .select_related('shop')
        .order_by('pickup_end')
    )
    return render(request, 'browse.html', {'foods': foods})

@login_required
def dashboard(request):
    _require_business(request)

    shops = Shop.objects.filter(owner=request.user)
    if not shops.exists():
        messages.error(request, "You don't have a shop yet. Please contact support.")
        return redirect("home")

    shop = shops.first()
    foods = shop.foods.order_by("-created_at")

    # Orders for any food belonging to this shop
    orders = (
        Order.objects
        .filter(food__shop=shop)
        .select_related("food", "customer")
        .order_by("-created_at")
    )

    now = timezone.now()
    stats = {
        "total": foods.count(),
        "active": foods.filter(is_active=True, pickup_end__gte=now).count(),
        "expired": foods.filter(pickup_end__lt=now).count(),
        "total_value": foods.aggregate(Sum("discounted_price"))["discounted_price__sum"] or 0,
        "orders_count": orders.count(),
        "orders_revenue": sum(
            (o.total for o in orders if o.effective_status != Order.CANCELLED),
            0,
        ),
    }

    return render(
        request,
        "dashboard/index.html",
        {
            "shop": shop,
            "foods": foods,
            "orders": orders[:20],
            "stats": stats,
            "now": now,
        },
    )


@login_required
def food_create(request):
    _require_business(request)

    shop = get_object_or_404(Shop, owner=request.user)

    if request.method == "POST":
        form = FoodForm(request.POST, request.FILES)
        if form.is_valid():
            food = form.save(commit=False)
            food.shop = shop
            food.save()
            messages.success(request, f"Listing “{food.title}” created.")
            return redirect("dashboard")
    else:
        form = FoodForm()

    return render(
        request,
        "dashboard/food_form.html",
        {"form": form, "mode": "create", "shop": shop},
    )


@login_required
def food_edit(request, pk):
    _require_business(request)

    shop = get_object_or_404(Shop, owner=request.user)
    food = get_object_or_404(Food, pk=pk, shop=shop)

    if request.method == "POST":
        form = FoodForm(request.POST, request.FILES, instance=food)
        if form.is_valid():
            form.save()
            messages.success(request, f"Listing “{food.title}” updated.")
            return redirect("dashboard")
    else:
        form = FoodForm(instance=food)

    return render(
        request,
        "dashboard/food_form.html",
        {"form": form, "mode": "edit", "shop": shop, "food": food},
    )


@login_required
def food_delete(request, pk):
    _require_business(request)

    shop = get_object_or_404(Shop, owner=request.user)
    food = get_object_or_404(Food, pk=pk, shop=shop)

    if request.method == "POST":
        title = food.title
        food.delete()
        messages.success(request, f"Listing “{title}” deleted.")
        return redirect("dashboard")

    return render(
        request,
        "dashboard/food_confirm_delete.html",
        {"food": food, "shop": shop},
    )

def food_detail(request, pk):
    food = get_object_or_404(
        Food, pk=pk, is_active=True, shop__is_active=True,
    )
    return render(request, "food_detail.html", {"food": food})


@login_required
def checkout(request, pk):
    food = get_object_or_404(Food, pk=pk, is_active=True, shop__is_active=True)

    if request.user.is_business():
        messages.error(request, "Business accounts can't place orders.")
        return redirect("browse")

    if food.quantity < 1:
        messages.error(request, "This item is sold out.")
        return redirect("browse")

    if request.method == "POST":
        fulfillment = request.POST.get("fulfillment", Order.PICKUP)
        quantity = max(1, min(int(request.POST.get("quantity", 1) or 1), food.quantity))

        subtotal = food.discounted_price * quantity
        delivery_fee = Decimal("0")
        address = ""
        courier = ""
        eta = timezone.now()

        if fulfillment == Order.DELIVERY:
            address = request.POST.get("delivery_address", "").strip()
            courier_key = request.POST.get("courier", "").strip()
            chosen = next((c for c in COURIERS if c["name"] == courier_key), None)

            if not chosen:
                messages.error(request, "Please choose a courier.")
                return render(request, "checkout.html", {"food": food, "couriers": COURIERS})

            if not address:
                messages.error(request, "Delivery address is required.")
                return render(request, "checkout.html", {"food": food, "couriers": COURIERS})

            courier = chosen["name"]
            delivery_fee = chosen["base_fee"]
            eta = timezone.now() + timedelta(minutes=random.randint(15, 40))
        else:
            # Pickup ready at the shop's listed end time (or now if already past)
            eta = max(timezone.now(), food.pickup_end)

        total = subtotal + delivery_fee

        with transaction.atomic():
            food.quantity -= quantity
            food.save(update_fields=["quantity"])

            order = Order.objects.create(
                customer=request.user,
                food=food,
                quantity=quantity,
                fulfillment=fulfillment,
                delivery_address=address,
                courier_name=courier,
                delivery_fee=delivery_fee,
                subtotal=subtotal,
                total=total,
                eta=eta,
            )

        return redirect("order_success", pk=order.pk)

    return render(request, "checkout.html", {"food": food, "couriers": COURIERS})


@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, "order_success.html", {"order": order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(customer=request.user).select_related("food", "food__shop")
    return render(request, "my_orders.html", {"orders": orders})

@login_required
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)

    if request.method != "POST":
        return redirect("my_orders")

    if not order.can_cancel:
        messages.error(request, "This order can no longer be cancelled.")
        return redirect("my_orders")

    with transaction.atomic():
        if order.food:
            order.food.quantity += order.quantity
            order.food.save(update_fields=["quantity"])
        order.status = Order.CANCELLED
        order.save(update_fields=["status"])

    messages.success(request, "Order cancelled and refunded.")
    return redirect("my_orders")

@login_required
def order_mark_picked_up(request, pk):
    _require_business(request)

    order = get_object_or_404(
        Order, pk=pk, food__shop__owner=request.user,
    )

    if request.method == "POST":
        if order.fulfillment != Order.PICKUP:
            messages.error(request, "Only pickup orders can be marked as picked up.")
        elif order.status != Order.PENDING:
            messages.error(request, "This order has already been finalized.")
        else:
            order.status = Order.DELIVERED
            order.save(update_fields=["status"])
            messages.success(request, f"Order #{order.pk} marked as picked up.")

    return redirect("dashboard")