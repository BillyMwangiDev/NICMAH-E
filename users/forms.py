"""
Custom user forms for NICMAH application.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with enhanced styling."""

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Enter your first name"}),
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Enter your last name"}),
    )

    email = forms.EmailField(
        required=True, widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "Enter your email address"})
    )

    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Enter your phone number"}),
    )

    role = forms.ChoiceField(
        choices=User.UserRole.choices, required=True, widget=forms.Select(attrs={"class": "form-input"})
    )

    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Enter your address"}),
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Enter your password"})
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Confirm your password"})
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role", "address", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove help text for cleaner UI
        for field_name in ["username", "password1", "password2"]:
            if field_name in self.fields:
                self.fields[field_name].help_text = None

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone = self.cleaned_data["phone"]
        user.role = self.cleaned_data["role"]
        user.address = self.cleaned_data["address"]

        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(user=user, phone=user.phone, address=user.address)
        return user


class CustomUserChangeForm(UserChangeForm):
    """Custom user change form for profile updates."""

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Enter your first name"}),
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Enter your last name"}),
    )

    email = forms.EmailField(
        required=True, widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "Enter your email address"})
    )

    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Enter your phone number"}),
    )

    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Enter your address"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "address")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password field from profile updates
        if "password" in self.fields:
            del self.fields["password"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone = self.cleaned_data["phone"]
        user.address = self.cleaned_data["address"]

        if commit:
            user.save()
            # Update user profile
            try:
                profile = user.userprofile
                profile.phone = user.phone
                profile.address = user.address
                profile.save()
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(user=user, phone=user.phone, address=user.address)
        return user


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information."""

    class Meta:
        model = UserProfile
        fields = ("bio", "website", "facebook", "twitter", "linkedin", "newsletter_subscription", "marketing_emails")
        widgets = {
            "bio": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Tell us about yourself..."}),
            "website": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://yourwebsite.com"}),
            "facebook": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://facebook.com/yourprofile"}
            ),
            "twitter": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://twitter.com/yourhandle"}),
            "linkedin": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://linkedin.com/in/yourprofile"}
            ),
            "newsletter_subscription": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 text-agro-green focus:ring-agro-green border-gray-300 rounded"}
            ),
            "marketing_emails": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 text-agro-green focus:ring-agro-green border-gray-300 rounded"}
            ),
        }
