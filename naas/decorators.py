from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def manager_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('employee_login')
        
        if not hasattr(request.user, 'employee'):
            messages.error(request, 'Access denied. Employee account required.')
            return redirect('employee_login')
        
        if request.user.employee.position != 'manager':
            messages.error(request, 'Access denied. Manager privileges required.')
            return redirect('employee_login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def clerk_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('employee_login')
        
        if not hasattr(request.user, 'employee'):
            messages.error(request, 'Access denied. Employee account required.')
            return redirect('employee_login')
        
        if request.user.employee.position not in ['clerk', 'manager']:
            messages.error(request, 'Access denied. Clerk or Manager privileges required.')
            return redirect('employee_login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def delivery_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('employee_login')
        
        if not hasattr(request.user, 'employee'):
            messages.error(request, 'Access denied. Employee account required.')
            return redirect('employee_login')
        
        if request.user.employee.position not in ['delivery', 'manager']:
            messages.error(request, 'Access denied. Delivery personnel or Manager privileges required.')
            return redirect('employee_login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def customer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('customer_login')
        
        if not hasattr(request.user, 'customer'):
            messages.error(request, 'Access denied. Customer account required.')
            return redirect('customer_login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view