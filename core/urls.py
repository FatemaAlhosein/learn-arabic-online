"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from curriculum import views as curriculum_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public certificate page (capability-URL, no auth required).
    # Top-level so URLs like /certificates/<code>/ are clean and shareable.
    path('certificates/<str:code>/', curriculum_views.certificate,
         name='certificate'),

    # Our signup view (must come BEFORE django.contrib.auth.urls so that
    # if both ever defined the same name, ours would win — currently we
    # only add 'signup', which Django's set doesn't include).
    path('accounts/', include('accounts.urls')),

    # Built-in auth views: provides URL names 'login', 'logout',
    # 'password_change', 'password_reset', etc. Templates live in
    # templates/registration/.
    path('accounts/', include('django.contrib.auth.urls')),

    # Public course catalogue + course detail pages.
    path('courses/', include('curriculum.urls')),

    # Authenticated dashboard (dispatches by role).
    path('dashboard/', include('dashboards.urls')),

    # Quiz player + submissions.
    path('', include('assessments.urls')),

    # Flashcard decks + study mode.
    path('', include('flashcards.urls')),

    # Assignments (teacher builder + student submission).
    path('', include('assignments.urls')),

    # Games
    path('games/', include('games.urls')),

    # Agenda tracker
    path('', include('agenda.urls')),

    # In-app notifications
    path('notifications/', include('notifications.urls')),

    # Cross-cutting public pages (home, about, etc.)
    path('', include('pages.urls')),
]

# Serve uploaded media files (/media/*) during development only.
# In production this is handled by nginx / S3 / a CDN, not Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
