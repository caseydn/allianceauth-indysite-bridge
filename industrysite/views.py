import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect

from .models import IndustrySiteAccount
from .tasks import notify_site_deactivate, push_account

logger = logging.getLogger(__name__)

SERVICES_PAGE = "services:services"


@login_required
@permission_required("industrysite.access_industrysite")
def activate(request):
    IndustrySiteAccount.objects.get_or_create(user=request.user)
    push_account.delay(request.user.pk, activate=True)
    messages.success(
        request,
        "Industry Site registration sent. Your characters will appear on the "
        "site shortly.",
    )
    return redirect(SERVICES_PAGE)


@login_required
def deactivate(request):
    account = IndustrySiteAccount.objects.filter(user=request.user).first()
    if account:
        # Unlink locally right away so the Services card flips to Disabled
        # immediately, then notify the site in the background (best-effort).
        user_id = request.user.pk
        main_id = account.main_character_id
        token = account.site_user_token
        account.delete()
        notify_site_deactivate.delay(user_id, main_id, token)
        messages.success(request, "Industry Site account disconnected.")
    return redirect(SERVICES_PAGE)
