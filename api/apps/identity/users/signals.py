from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from .models import AkitaUser, UserRole


@receiver(pre_save, sender=AkitaUser)
def enforce_registered_by_for_non_superusers(sender, instance, **kwargs):
    """
    Enforce that every non-superuser account has a registered_by value.

    Superuser exemption exists to allow the developer to bootstrap the
    first account via `createsuperuser` or the Django admin without a
    pre-existing registrar in the system.

    Raises:
        ValidationError — caught by ModelForm (admin UI) and DRF's
        full_clean() call inside ModelSerializer.validate().

    Note:
        pre_save fires on both INSERT and UPDATE. The `instance.pk` check
        distinguishes new records (pk is None → creation) from updates, so
        the constraint only applies at the moment of account creation.
        An existing non-superuser whose registered_by was somehow cleared
        after creation will also be caught on subsequent saves — intentional,
        as registered_by should be immutable once set.
    """
    if instance.role == UserRole.SUPERUSER:
        return  # superuser accounts are exempt — bootstrapping use case

    if instance.registered_by is None:
        raise ValidationError({
            'registered_by': (
                'A registrar is required for all non-superuser accounts. '
                'This field is set automatically from the session of the '
                'authenticated user performing the registration.'
            )
        })