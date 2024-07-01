import pytest

from tempfile import NamedTemporaryFile

from pulp_smash.pulp3.utils import (
    gen_distribution,
    gen_repo,
)
from pulp_smash.pulp3.bindings import monitor_task

from pulpcore.client.pulp_container import (
    ContainerContainerDistribution,
    ContainerContainerRepository,
)

from pulpcore.client.pulp_file import (
    RepositoryAddRemoveContent,
)


@pytest.fixture
def containerfile_name():
    """A fixture for a basic container file used for building images."""
    with NamedTemporaryFile() as containerfile:
        containerfile.write(
            b"""FROM busybox:latest
# Copy a file using COPY statement. Use the relative path specified in the 'artifacts' parameter.
COPY foo/bar/example.txt /tmp/inside-image.txt
# Print the content of the file when the container starts
CMD ["cat", "/tmp/inside-image.txt"]"""
        )
        containerfile.flush()
        yield containerfile.name


def test_build_image_from_artifact(
    artifacts_api_client,
    container_repository_api,
    container_distribution_api,
    gen_object_with_cleanup,
    containerfile_name,
    local_registry,
):
    """Test if a user can build an OCI image."""
    with NamedTemporaryFile() as text_file:
        text_file.write(b"some text")
        text_file.flush()
        artifact = gen_object_with_cleanup(artifacts_api_client, text_file.name)

    repository = gen_object_with_cleanup(
        container_repository_api, ContainerContainerRepository(**gen_repo())
    )

    artifacts = '{{"{}": "foo/bar/example.txt"}}'.format(artifact.pulp_href)
    build_response = container_repository_api.build_image(
        repository.pulp_href, containerfile=containerfile_name, artifacts=artifacts
    )
    monitor_task(build_response.task)

    distribution = gen_object_with_cleanup(
        container_distribution_api,
        ContainerContainerDistribution(**gen_distribution(repository=repository.pulp_href)),
    )

    local_registry.pull(distribution.base_path)
    image = local_registry.inspect(distribution.base_path)
    assert image[0]["Config"]["Cmd"] == ["cat", "/tmp/inside-image.txt"]


def test_build_image_from_repo_version(
    containerfile_name,
    container_distribution_api,
    container_repository_api,
    file_bindings,
    file_content_unit_with_name_factory,
    file_repo_with_auto_publish,
    gen_object_with_cleanup,
    local_registry,
):
    """Test if a user can build an OCI image."""
    repository = gen_object_with_cleanup(
        container_repository_api, ContainerContainerRepository(**gen_repo())
    )

    files = {
        "txt": file_content_unit_with_name_factory("foo/bar/example.txt"),
    }

    units_to_add = list(map(lambda f: f.pulp_href, files.values()))
    data = RepositoryAddRemoveContent(add_content_units=units_to_add)
    monitor_task(
        file_bindings.RepositoriesFileApi.modify(file_repo_with_auto_publish.pulp_href, data).task
    )

    build_response = container_repository_api.build_image(
        containerfile=containerfile_name,
        repo_version=f"{file_repo_with_auto_publish.pulp_href}versions/1/",
        container_container_repository_href=repository.pulp_href,
    )
    monitor_task(build_response.task)

    distribution = gen_object_with_cleanup(
        container_distribution_api,
        ContainerContainerDistribution(**gen_distribution(repository=repository.pulp_href)),
    )

    local_registry.pull(distribution.base_path)
    image = local_registry.inspect(distribution.base_path)
    assert image[0]["Config"]["Cmd"] == ["cat", "/tmp/inside-image.txt"]
