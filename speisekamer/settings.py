import os
from pathlib import Path
from datetime import timedelta


# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = 'django-insecure-l+ip+3p)m#t^tv#5#@x#-=+5i!fj-9h&dj--j80u5xo_bycf(o'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost','http://localhost:5173/']

# Applications
INSTALLED_APPS = [
    'jazzmin', 
    'django.contrib.admin',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',


    # Your apps
    'authentication',
    'customers',
    'leads',
    'workflow',
    'design',
    'production_installation',
    'architect',

    'catalog',  
    'pricing',         # Product catalog management

  

    'whitenoise.runserver_nostatic',
    
]

# Middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URLs
ROOT_URLCONF = 'speisekamer.urls'
WSGI_APPLICATION = 'speisekamer.wsgi.application'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Database: Default is SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


JAZZMIN_SETTINGS = {
    "site_title": "Speisekamer Admin",
    "site_header": "Kitchen Catalog Management",
    "site_brand": "Speisekamer",
    "site_logo": "images/logo.png",
    "welcome_sign": "Welcome to Kitchen Catalog Admin",
    "copyright": "Speisekamer Ltd",
    "search_model": ["catalog.Product", "catalog.ProductVariant"],
    
    # UI Tweaks
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    
    # Top Menu
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
        {"model": "auth.User"},
    ],
    
    # User Menu
    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
        {"model": "auth.user"}
    ],
    
    # Side Menu
    "show_ui_builder": True,
    
    # Custom CSS/JS
    "custom_css": "admin/css/custom.css",
    "custom_js": "admin/js/custom.js",
    
    # Icons (FontAwesome)
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "catalog.Category": "fas fa-th-large",
        "catalog.Brand": "fas fa-tags",
        "catalog.Product": "fas fa-box",
        "catalog.ProductVariant": "fas fa-cubes",
        "catalog.Color": "fas fa-palette",
        "customers.Customer": "fas fa-user-tie",
        "quotations.Quotation": "fas fa-file-invoice-dollar",
    },
    
    # Related Modal
    "related_modal_active": True,
    

    
    # Color Scheme
    "theme": "default",  # or "darkly", "flatly", "minty", "pulse", "sandstone", "united"
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

# If using custom CSS/JS (add after basic setup works)
JAZZMIN_SETTINGS.update({
    "custom_css": "admin/css/speisekamer-admin.css",
    "custom_js": "admin/js/speisekamer-admin.js",
})
# Custom User model
AUTH_USER_MODEL = 'authentication.CustomUser'

# JWT Auth
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('SIGNING_KEY', SECRET_KEY),
}

# DRF Auth
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
  "http://localhost:5173",

]


# Password Validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# I18N
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
