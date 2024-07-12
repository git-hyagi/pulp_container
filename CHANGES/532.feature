Added a limit of 4mb to the size of manifests and signatures as a safeguard to OOM DoS attack
during sync tasks and updated the Nginx snippet to also limit the size of the body for these endpoints.
