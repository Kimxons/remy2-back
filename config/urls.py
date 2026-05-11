from django.contrib import admin
from django.urls import path, re_path, include
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf.urls.static import static
from django.conf import settings
from django.views.static import serve  # Required to serve files in production
from user_module.views import (
    DashboardStatsView,
    DashboardJobsView,
    DashboardNotificationsView,
    DashboardNotificationReadView,
    DashboardNotificationUnreadView,
    DashboardSummaryView,
    ProfileAliasView,
    ProfilePictureView,
)

admin.site.site_header = "RemyInk!"
admin.site.site_title = "Job Matching"
admin.site.index_title = "Welcome to the Freelancer Marketplace"


def payment_verify_redirect(request):
    frontend_base = str(getattr(settings, 'FRONTEND_URL', '') or '').strip().rstrip('/')
    target_base = frontend_base or 'http://localhost:3000'

    query = {}
    reference = (request.GET.get('reference') or request.GET.get('trxref') or '').strip()
    trxref = (request.GET.get('trxref') or '').strip()
    payment_email = ''

    if reference:
        try:
            from payment_gateway.models import Payment

            payment = Payment.objects.select_related('user', 'job__client').filter(
                reference=reference
            ).first()
            if payment:
                payment_email = (
                    getattr(payment.user, 'email', None)
                    or getattr(getattr(payment, 'job', None), 'client', None).email
                ) or ''
        except Exception:
            payment_email = ''

    if reference:
        query['reference'] = reference
    if trxref and trxref != reference:
        query['trxref'] = trxref
    if payment_email:
        query['email'] = payment_email

    query['payment'] = 'verified'
    query['role'] = 'CLIENT'

    destination = f"{target_base}/login"
    if query:
        destination = f"{destination}?{urlencode(query)}"

    return HttpResponseRedirect(destination)

urlpatterns = [
    # path('', lambda request: redirect('http://localhost:5173')),
    
    path('admin/', admin.site.urls),
    
    path('api/orders/', include('orders.urls')),
    path('api/chat/', include('chat.urls')),
    path('api/users/', include('user_module.urls')),
    # Backward-compatible dashboard aliases
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats-alias'),
    path('api/dashboard/jobs/', DashboardJobsView.as_view(), name='dashboard-jobs-alias'),
    path('api/dashboard/notifications/', DashboardNotificationsView.as_view(), name='dashboard-notifications-alias'),
    path('api/dashboard/notifications/<str:notification_id>/read/', DashboardNotificationReadView.as_view(), name='dashboard-notification-read-alias'),
    path('api/dashboard/notifications/<str:notification_id>/unread/', DashboardNotificationUnreadView.as_view(), name='dashboard-notification-unread-alias'),
    path('api/dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary-alias'),
    path('api/profile/alias/', ProfileAliasView.as_view(), name='profile-alias-api-alias'),
    path('profile/alias/', ProfileAliasView.as_view(), name='profile-alias-root-alias'),
    path('api/profile/picture/', ProfilePictureView.as_view(), name='profile-picture-api-alias'),
    path('profile/picture/', ProfilePictureView.as_view(), name='profile-picture-root-alias'),
    path('api/jobs/', include('jobs.urls')),
    path('api/payment/', include('pay_freelancer.urls')),
    path('api/payments/', include('payment_gateway.urls')),
    path('payment/verify', payment_verify_redirect, name='payment-verify-redirect'),
    
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]  