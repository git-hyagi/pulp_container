# Limit the size of Manifests and Signatures

It is possible to configure Pulp to block the synchronization and upload of image Manifests and/or
Signatures if they exceed a defined size. A use case for this feature is to avoid OOM DoS attacks
when synchronizing remote repositories with malicious or compromised containter images.
To implement this, use the following settings:
```
MANIFEST_PAYLOAD_MAX_SIZE=<bytes>
SIGNATURE_PAYLOAD_MAX_SIZE=<bytes>
```

!!! info
    By default, there is no definition for these settings, meaning that no limit will be enforced.


!!! note
    A common value adopted by other registries is to set these values to 4MB (4000000).
