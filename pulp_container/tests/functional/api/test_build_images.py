import pytest

from tempfile import NamedTemporaryFile

from pulp_smash.pulp3.utils import (
    gen_distribution,
    gen_repo,
)
from pulp_smash.pulp3.bindings import monitor_task

from pulpcore.client.pulp_container import (
    ApiException,
    ContainerContainerDistribution,
    ContainerContainerRepository,
)


@pytest.fixture
def containerfile_name():
    """A fixture for a basic container file used for building images."""
    with NamedTemporaryFile() as containerfile:
        containerfile.write(
            b"""FROM quay.io/quay/busybox:latest
# Copy a file using COPY statement. Use the relative path specified in the 'artifacts' parameter.
COPY foo/bar/example.txt /tmp/inside-image.txt
# Print the content of the file when the container starts
CMD ["cat", "/tmp/inside-image.txt"]"""
        )
        containerfile.flush()
        yield containerfile.name


@pytest.fixture
def create_file_and_container_repos_with_sample_data(
    container_repository_api,
    file_bindings,
    file_repository_factory,
    gen_object_with_cleanup,
    tmp_path_factory,
):
    container_repo = gen_object_with_cleanup(
        container_repository_api, ContainerContainerRepository(**gen_repo())
    )

    filename = tmp_path_factory.mktemp("fixtures") / "example.txt"
    filename.write_bytes(b"test content")
    file_repo = file_repository_factory(autopublish=True)
    upload_task = file_bindings.ContentFilesApi.create(
        relative_path="foo/bar/example.txt", file=filename, repository=file_repo.pulp_href
    ).task
    monitor_task(upload_task)

    return container_repo, file_repo


@pytest.fixture
def build_image(container_repository_api):
    def _build_image(repository, containerfile, repo_version=None):
        build_response = container_repository_api.build_image(
            container_container_repository_href=repository,
            containerfile=containerfile,
            repository_version=repo_version,
        )
        monitor_task(build_response.task)

    return _build_image


def test_build_image(
    build_image,
    containerfile_name,
    container_distribution_api,
    create_file_and_container_repos_with_sample_data,
    delete_orphans_pre,
    gen_object_with_cleanup,
    local_registry,
):
    """Test build an OCI image from a file repository_version."""
    container_repo, file_repo = create_file_and_container_repos_with_sample_data
    build_image(
        container_repo.pulp_href,
        containerfile_name,
        repository_version=f"{file_repo.pulp_href}versions/1/",
    )

    distribution = gen_object_with_cleanup(
        container_distribution_api,
        ContainerContainerDistribution(**gen_distribution(repository=container_repo.pulp_href)),
    )

    local_registry.pull(distribution.base_path)
    image = local_registry.inspect(distribution.base_path)
    assert image[0]["Config"]["Cmd"] == ["cat", "/tmp/inside-image.txt"]


def test_build_image_from_repo_version_with_anon_user(
    build_image,
    containerfile_name,
    create_file_and_container_repos_with_sample_data,
    delete_orphans_pre,
    gen_user,
):
    """Test if a user without permission to file repo can build an OCI image."""
    user_helpless = gen_user(
        model_roles=[
            "container.containerdistribution_collaborator",
            "container.containerrepository_content_manager",
        ]
    )
    container_repo, file_repo = create_file_and_container_repos_with_sample_data
    with user_helpless, pytest.raises(ApiException):
        build_image(
            container_repo.pulp_href,
            containerfile_name,
            repository_version=f"{file_repo.pulp_href}versions/1/",
        )


def test_build_image_from_repo_version_with_creator_user(
    build_image,
    containerfile_name,
    create_file_and_container_repos_with_sample_data,
    delete_orphans_pre,
    gen_user,
):
    """Test if a user (with the expected permissions) can build an OCI image."""
    user = gen_user(
        model_roles=[
            "container.containerdistribution_collaborator",
            "container.containerrepository_content_manager",
            "file.filerepository_viewer",
        ]
    )
    container_repo, file_repo = create_file_and_container_repos_with_sample_data
    with user:
        build_image(
            container_repo.pulp_href,
            containerfile_name,
            repository_version=f"{file_repo.pulp_href}versions/1/",
        )
