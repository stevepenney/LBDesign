from django.contrib.auth.models import AbstractUser
from django.db import models


class Organisation(models.Model):
    """
    A merchant or pre-nailer business entity.
    Users belong to an Organisation and inherit its access rights.
    """
    name = models.CharField(max_length=200)
    is_merchant = models.BooleanField(
        default=False,
        help_text='Grants access to pricing information and the estimation tool.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom user model. Extends AbstractUser so we can add organisation
    membership and role without losing Django's built-in auth machinery.
    """

    class Role(models.TextChoices):
        MERCHANT_USER = 'merchant_user', 'Merchant User'
        LB_ADMIN = 'lb_admin', 'Lumberbank Admin'
        LB_DETAILING = 'lb_detailing', 'Lumberbank Detailing Team'

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    role = models.CharField(
        max_length=20,
        choices=Role,
        default=Role.MERCHANT_USER,
    )

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_lb_admin(self):
        return self.role == self.Role.LB_ADMIN

    @property
    def is_lb_detailing(self):
        return self.role == self.Role.LB_DETAILING

    @property
    def is_merchant_user(self):
        return self.role == self.Role.MERCHANT_USER

    @property
    def can_access_pricing(self):
        """True if user's organisation has merchant access, or user is LB staff."""
        if self.role in (self.Role.LB_ADMIN, self.Role.LB_DETAILING):
            return True
        return self.organisation is not None and self.organisation.is_merchant
