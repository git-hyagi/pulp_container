# Build Images

!!! warning

    All container build APIs are in tech preview. Backwards compatibility when upgrading is not
    guaranteed.

Users can add new images to a container repository by uploading a Containerfile. The syntax for
Containerfile is the same as for a Dockerfile. The same REST API endpoint also accepts a JSON
string that maps artifacts in Pulp to a filename. Any file passed in are available inside the
build container at `/pulp_working_directory`.

## Create a Container Repository

```bash
CONTAINER_REPO=$(pulp container repository create --name building | jq -r '.pulp_href')
```

## Create a File Repository and populate it

```bash
FILE_REPO=$(pulp file repository create --name bar --autopublish | jq -r '.pulp_href')

echo 'Hello world!' > example.txt

pulp file content upload --relative-path foo/bar/example.txt \
--file ./example.txt --repository bar
```

## Create a Containerfile

```bash
echo 'FROM centos:7

# Copy a file using COPY statement. Use the relative path specified in the 'artifacts' parameter.
COPY foo/bar/example.txt /inside-image.txt

# Print the content of the file when the container starts
CMD ["cat", "/inside-image.txt"]' >> Containerfile
```

## Build an OCI image

```bash
TASK_HREF=$(http --form POST :$CONTAINER_REPO'build_image/' "containerfile@./Containerfile" \
repo_version=${FILE_REPO}versions/1/ | jq -r '.task')
```


!!! warning

    File repositories synced with on-demand remotes will not automatically pull the missing artifacts.
    Trying to build using a file that is not yet pulled will fail.
