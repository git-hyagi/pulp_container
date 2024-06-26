import subprocess
import pytest
import re

from uuid import uuid4

from pulp_container.tests.functional.constants import (
    REGISTRY_V2,
    REGISTRY_V2_FEED_URL,
    PULP_HELLO_WORLD_REPO,
    PULP_FIXTURE_1,
)


@pytest.fixture
def pull_through_distribution(
    gen_object_with_cleanup,
    container_pull_through_remote_api,
    container_pull_through_distribution_api,
):
    def _pull_through_distribution(includes, excludes):
        remote = gen_object_with_cleanup(
            container_pull_through_remote_api,
            {
                "name": str(uuid4()),
                "url": REGISTRY_V2_FEED_URL,
                "includes": includes,
                "excludes": excludes,
            },
        )
        distribution = gen_object_with_cleanup(
            container_pull_through_distribution_api,
            {"name": str(uuid4()), "base_path": str(uuid4()), "remote": remote.pulp_href},
        )
        return distribution

    return _pull_through_distribution


@pytest.fixture
def pull_and_verify(
    capfd,
    delete_orphans_pre,
    local_registry,
    registry_client,
):
    def _pull_and_verify(images, pull_through_distribution, includes, excludes):
        distr = pull_through_distribution(includes, excludes)
        for _, image_path in enumerate(images, start=1):
            remote_image_path = f"{REGISTRY_V2}/{image_path}"
            local_image_path = f"{distr.base_path}/{image_path}"

            if excludes and re.match(".*fixture.*", image_path):
                with pytest.raises(subprocess.CalledProcessError):
                    local_registry.pull(local_image_path)
                assert (
                    re.search(
                        ".*Repository not found.*",
                        capfd.readouterr().err,
                    )
                    is not None
                )
                continue
            local_registry.pull(local_image_path)
            local_image = local_registry.inspect(local_image_path)
            registry_client.pull(remote_image_path)
            remote_image = registry_client.inspect(remote_image_path)
            assert local_image[0]["Id"] == remote_image[0]["Id"]

    return _pull_and_verify


def test_no_filter(pull_through_distribution, pull_and_verify):
    images = [f"{PULP_FIXTURE_1}:manifest_a", f"{PULP_FIXTURE_1}:manifest_b"]
    includes = None
    excludes = []
    pull_and_verify(images, pull_through_distribution, includes, excludes)


def test_filter_exclude_with_regex(pull_through_distribution, pull_and_verify):
    images = [f"{PULP_FIXTURE_1}:manifest_a", f"{PULP_FIXTURE_1}:manifest_b"]
    includes = []
    excludes = ["pulp*"]
    pull_and_verify(images, pull_through_distribution, includes, excludes)


def test_filter_exclude(pull_through_distribution, pull_and_verify):
    images = [f"{PULP_FIXTURE_1}:manifest_a", f"{PULP_FIXTURE_1}:manifest_b"]
    includes = []
    excludes = ["pulp/test-fixture-1"]
    pull_and_verify(images, pull_through_distribution, includes, excludes)


def test_filter_include_and_exclude(pull_through_distribution, pull_and_verify):
    images = [
        f"{PULP_FIXTURE_1}:manifest_a",
        f"{PULP_FIXTURE_1}:manifest_b",
        f"{PULP_HELLO_WORLD_REPO}:linux",
    ]
    includes = ["*hello*"]
    excludes = ["*fixture*"]
    pull_and_verify(images, pull_through_distribution, includes, excludes)
