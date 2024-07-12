Added support to the `MANIFEST_PAYLOAD_MAX_SIZE` and `SIGNATURE_PAYLOAD_MAX_SIZE` settings to define
limits (for the size of Manifests and Signatures) to protect against OOM DoS attacks during synchronization tasks
and image uploads.
Additionally, the Nginx snippet has been updated to enforce the limit for these endpoints.
Modified the internal logic of Blob uploads to read the receiving layers in chunks,
thereby reducing the memory footprint of the process.
