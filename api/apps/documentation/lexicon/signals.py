from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Collocation


@receiver(m2m_changed, sender=Collocation.other_entries.through)
def prevent_collocation_overlap(sender, instance, action, pk_set, **kwargs):
    if action == 'pre_add' and instance.basic_entry_id:
        raise ValidationError(
            "The basic word entry cannot be selected in the connected collocation entries (other_entries)."
        )
    