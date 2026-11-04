from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Food


class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (User.CUSTOMER, "I'm a customer"),
            (User.BUSINESS, "I'm a business"),
        ],
        initial=User.CUSTOMER,
        widget=forms.RadioSelect(attrs={"class": "role-radio"}),
    )

    shop_name = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Sunrise Bakery"}),
    )
    shop_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Street, area, city"}),
    )
    shop_cuisine = forms.CharField(
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Bakery, Japanese, Grocery"}),
    )

    class Meta:
        model = User
        fields = ("username", "email")

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")

        if role == User.BUSINESS:
            for field, label in (
                ("shop_name", "Shop name"),
                ("shop_address", "Shop address"),
                ("shop_cuisine", "Cuisine"),
            ):
                if not cleaned.get(field):
                    self.add_error(field, f"{label} is required for business accounts.")

        return cleaned
    

class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = (
            "title",
            "description",
            "emoji",
            "image",
            "original_price",
            "discounted_price",
            "quantity",
            "pickup_start",
            "pickup_end",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "pickup_start": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "pickup_end": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pickup_start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["pickup_end"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("pickup_start")
        end = cleaned.get("pickup_end")
        orig = cleaned.get("original_price")
        disc = cleaned.get("discounted_price")

        if start and end and end <= start:
            self.add_error("pickup_end", "Pickup end must be after pickup start.")

        if orig is not None and disc is not None and disc >= orig:
            self.add_error("discounted_price", "Discounted price must be less than original price.")

        return cleaned