
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User, Customer, Employee, Subscription, Payment, Delivery, Complaint, Publication, IssueReport,Product
from django.utils import timezone
from datetime import timedelta

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'address', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data['phone']
        user.address = self.cleaned_data['address']
        
        if commit:
            user.save()
            customer = Customer.objects.create(user=user)
        
        return user

class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['publication', 'start_date', 'end_date', 'delivery_address', 'quantity']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'delivery_address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['publication'].queryset = Publication.objects.filter(is_available=True)
        self.fields['start_date'].initial = timezone.now().date()
        self.fields['end_date'].initial = timezone.now().date() + timedelta(days=30)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['subscription', 'amount', 'payment_method', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['subscription', 'delivery_person', 'delivery_date', 'delivery_status', 'notes']
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['subject', 'description']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Describe your issue in detail...'}),
        }

class PauseDeliveryForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    reason = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for pausing delivery'}))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError("End date must be after start date.")
            if start_date < timezone.now().date():
                raise forms.ValidationError("Start date cannot be in the past.")
        
        return cleaned_data

class IssueReportForm(forms.ModelForm):
    class Meta:
        model = IssueReport
        fields = ['issue_type', 'description']
        widgets = {
            'issue_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Describe the issue in detail...'
            }),
        }

class DeliveryAssignmentForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['subscription', 'delivery_person', 'delivery_date', 'notes']
        widgets = {
            'subscription': forms.Select(attrs={'class': 'form-control'}),
            'delivery_person': forms.Select(attrs={'class': 'form-control'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active subscriptions
        self.fields['subscription'].queryset = Subscription.objects.filter(status='active')
        # Only show delivery persons
        self.fields['delivery_person'].queryset = Employee.objects.filter(position='delivery', is_active=True)
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'image', 'description']
