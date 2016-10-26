from pyramid.settings import aslist
from pyramid.security import Allow, Authenticated, ALL_PERMISSIONS

from . import log


def includeme(config):
    """
    Configures additional security utilities
    """
    settings = config.registry.settings

    assert 'occams.groups' in settings

    mappings = {}

    for entry in aslist(settings['occams.groups'], flatten=False):
        (site_domain, app_domain) = entry.split('=')
        mappings[site_domain.strip()] = app_domain.strip()

    config.add_request_method(
        lambda request: mappings, name='group_mappings', reify=True)

    log.info('Configured groups')


def groupfinder(identity, request):
    """
    Parse the groups from the identity into internal app groups
    """

    if 'groups' not in identity:
        log.warn('Groups has not been set in the repoze identity!')
        return []

    mappings = request.group_mappings

    groups = [mappings[g] if g in mappings else g for g in identity['groups']]

    return groups


class RootFactory(dict):

    __acl__ = [
        (Allow, 'administrator', ALL_PERMISSIONS),
        (Allow, Authenticated, 'view')]

    def __init__(self, request):
        self.request = request
