import json
from json.decoder import JSONDecodeError

from gettext import gettext as _

from contextlib import suppress

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand

from pulpcore.plugin.cache import SyncContentCache

from pulp_container.app.models import ContainerDistribution, Manifest


class Command(BaseCommand):
    """
    A management command to handle the initialization of empty architecture and os fields for
    container images.

    This command retrieves a list of manifests that have a null architecture field and
    populates them with the appropriate architecture definitions sourced from the corresponding
    ConfigBlob.
    """

    help = _(__doc__)

    def handle(self, *args, **options):
        manifests_updated_count = 0

        manifests_v1 = Manifest.objects.filter(architecture__isnull=True)
        manifests_updated_count += self.update_manifests(manifests_v1)

        self.stdout.write(
            self.style.SUCCESS("Successfully updated %d manifests." % manifests_updated_count)
        )

        if settings.CACHE_ENABLED and manifests_updated_count != 0:
            base_paths = ContainerDistribution.objects.values_list("base_path", flat=True)
            if base_paths:
                SyncContentCache().delete(base_key=base_paths)

            self.stdout.write(self.style.SUCCESS("Successfully flushed the cache."))

    def update_manifests(self, manifests_qs):
        manifests_updated_count = 0
        manifests_to_update = []
        for manifest in manifests_qs.iterator():
            # suppress non-existing/already migrated artifacts and corrupted JSON files
            with suppress(ObjectDoesNotExist, JSONDecodeError):
                manifest_data = json.loads(manifest.data)
                manifest.init_metadata(manifest_data)
                manifests_to_update.append(manifest)

            if len(manifests_to_update) > 1000:
                fields_to_update = ["architecture", "os"]
                manifests_qs.model.objects.bulk_update(
                    manifests_to_update,
                    fields_to_update,
                )
                manifests_updated_count += len(manifests_to_update)
                manifests_to_update.clear()

        if manifests_to_update:
            fields_to_update = ["architecture", "os"]
            manifests_qs.model.objects.bulk_update(
                manifests_to_update,
                fields_to_update,
            )
            manifests_updated_count += len(manifests_to_update)

        return manifests_updated_count
