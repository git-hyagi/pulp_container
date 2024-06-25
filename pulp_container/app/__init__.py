from pulpcore.plugin import PulpPluginAppConfig

try:
    import debugpy
    debugpy.listen(('0.0.0.0',5678))
    debugpy.wait_for_client()
except:
    pass
class PulpContainerPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the container plugin."""

    name = "pulp_container.app"
    label = "container"
    version = "2.21.0.dev"
    python_package_name = "pulp-container"

    def ready(self):
        super().ready()
        from . import checks
