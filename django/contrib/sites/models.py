from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible


SITE_CACHE = {}


class SiteManager(models.Manager):

    def get_current(self, request=None):
        """
        Returns the current ``Site`` based on the SITE_ID in the
        project's settings or the domain in the request. The
        ``Site`` object is cached the first time it's retrieved
        from the database.
        """
        from django.conf import settings
        if hasattr(settings, 'SITE_ID'):
            sid = settings.SITE_ID
            try:
                current_site = SITE_CACHE[sid]
            except KeyError:
                current_site = self.get(pk=sid)
                SITE_CACHE[sid] = current_site
        elif request:
            domain = request.META['SERVER_NAME']
            try:
                current_site = SITE_CACHE[domain]
            except KeyError:
                current_site = self.get(domain=domain)
                SITE_CACHE[domain] = current_site
        else:
            raise Site.DoesNotExist()
        return current_site

    def clear_cache(self):
        """Clears the ``Site`` object cache."""
        global SITE_CACHE
        SITE_CACHE = {}


@python_2_unicode_compatible
class Site(models.Model):

    domain = models.CharField(_('domain name'), max_length=100, db_index=True)
    name = models.CharField(_('display name'), max_length=50)
    objects = SiteManager()

    class Meta:
        db_table = 'django_site'
        verbose_name = _('site')
        verbose_name_plural = _('sites')
        ordering = ('domain',)

    def __str__(self):
        return self.domain

    def save(self, *args, **kwargs):
        super(Site, self).save(*args, **kwargs)
        # Cached information will likely be incorrect now.
        if self.id in SITE_CACHE:
            del SITE_CACHE[self.id]

    def delete(self):
        pk = self.pk
        super(Site, self).delete()
        try:
            del SITE_CACHE[pk]
        except KeyError:
            pass


@python_2_unicode_compatible
class RequestSite(object):
    """
    A class that shares the primary interface of Site (i.e., it has
    ``domain`` and ``name`` attributes) but gets its data from a Django
    HttpRequest object rather than from a database.

    The save() and delete() methods raise NotImplementedError.
    """
    def __init__(self, request):
        self.domain = self.name = request.get_host()

    def __str__(self):
        return self.domain

    def save(self, force_insert=False, force_update=False):
        raise NotImplementedError('RequestSite cannot be saved.')

    def delete(self):
        raise NotImplementedError('RequestSite cannot be deleted.')


def get_current_site(request):
    """
    Checks if contrib.sites is installed and returns either the current
    ``Site`` object or a ``RequestSite`` object based on the request.
    """
    if Site._meta.installed:
        current_site = Site.objects.get_current(request)
    else:
        current_site = RequestSite(request)
    return current_site
