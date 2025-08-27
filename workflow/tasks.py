# workflow/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta

from customers.models import Customer  # Or wherever your Customer is
from django.db import transaction


