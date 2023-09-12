#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

"""This module declares the base images versions for Python connectors.
To add a new base version please implement a new class that inherits from AirbytePythonConnectorBaseImage.
"""

import inspect
import sys
from abc import ABC
from typing import Final, Set, Type

import dagger
from base_images import common, errors


class PythonBase(common.BaseBaseImage):
    """
    This enum declares the Python base images that can be use to build our own base image for python.
    We use the image digest (the a sha256) to ensure that the image is not changed for reproducibility.
    """

    PYTHON_3_9 = {
        # https://hub.docker.com/layers/library/python/3.9.18-bookworm/images/sha256-40582fe697811beb7bfceef2087416336faa990fd7e24984a7c18a86d3423d58
        dagger.Platform("linux/amd64"): common.PlatformAwareDockerImage(
            image_name="python",
            tag="3.9.18-bookworm",
            sha="40582fe697811beb7bfceef2087416336faa990fd7e24984a7c18a86d3423d58",
            platform=dagger.Platform("linux/amd64"),
        ),
        # https://hub.docker.com/layers/library/python/3.9.18-bookworm/images/sha256-0d132e30eb9325d53c790738e5478e9abffc98b69115e7de429d7c6fc52dddac
        dagger.Platform("linux/arm64"): common.PlatformAwareDockerImage(
            image_name="python",
            tag="3.9.18-bookworm",
            sha="0d132e30eb9325d53c790738e5478e9abffc98b69115e7de429d7c6fc52dddac",
            platform=dagger.Platform("linux/arm64"),
        ),
    }


class AirbytePythonConnectorBaseImage(common.AirbyteConnectorBaseImage, ABC):
    """An abstract class that represents an Airbyte Python base image."""

    image_name: Final[str] = "airbyte-python-connector-base"

    EXPECTED_ENV_VARS: Set[str] = {
        "PYTHON_VERSION",
        "PYTHON_PIP_VERSION",
        "PYTHON_GET_PIP_SHA256",
        "PYTHON_GET_PIP_URL",
        "HOME",
        "PATH",
        "LANG",
        "GPG_KEY",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
        "PYTHON_SETUPTOOLS_VERSION",
        "OTEL_TRACES_EXPORTER",
        "OTEL_TRACE_PARENT",
        "TRACEPARENT",
    }

    async def run_sanity_checks(self):
        await super().run_sanity_checks()
        await self.check_env_vars()

    async def check_env_vars(self):
        """Checks that the expected environment variables are set on the base image.
        The EXPECTED_ENV_VARS were set on all our certified python connectors that were not using this base image
        We want to make sure that they are still set on all our connectors to avoid breaking changes.

        Raises:
            errors.SanityCheckError: Raised if a sanity check fails: the printenv command could not be executed or an expected variable is not set.
        """
        try:
            printenv_output: str = await self.container.with_exec(["printenv"], skip_entrypoint=True).stdout()
        except dagger.ExecError as e:
            raise errors.SanityCheckError("failed to run printenv.") from e
        env_vars = set([line.split("=")[0] for line in printenv_output.splitlines()])
        missing_env_vars = self.EXPECTED_ENV_VARS - env_vars
        if missing_env_vars:
            raise errors.SanityCheckError(f"missing environment variables: {missing_env_vars}")


class _0_1_0(AirbytePythonConnectorBaseImage):

    base_base_image: Final[PythonBase] = PythonBase.PYTHON_3_9

    TIMEZONE: Final[str] = "Etc/UTC"
    # This should be a final class attribute if the base_base_image attribute is Final
    EXPECTED_PYTHON_VERSION: Final[str] = "3.9.18"
    EXPECTED_PIP_VERSION: str = "23.2.1"

    changelog_entry: str = (
        "Declare our first base image version. It uses Python 3.9.18 on a Debian 11 (Bookworm) system with Pip 23.2.1 and UTC timezone."
    )

    @property
    def container(self) -> dagger.Container:
        return self.base_container.with_exec(["ln", "-snf", f"/usr/share/zoneinfo/{self.TIMEZONE}", "/etc/localtime"]).with_exec(
            ["pip", "install", "--upgrade", f"pip=={self.EXPECTED_PIP_VERSION}"]
        )

    async def run_sanity_checks(self):
        await super().run_sanity_checks()
        await self.check_python_version()
        await self.check_pip_version()
        await self.check_time_zone()
        await self.check_bash_is_installed()

    async def check_python_version(self):
        """Checks that the python version is the expected one.

        Raises:
            errors.SanityCheckError: Raised if the python --version command could not be executed or if the outputted version is not the expected one.
        """
        try:
            python_version_output: str = await self.container.with_exec(["python", "--version"], skip_entrypoint=True).stdout()
        except dagger.ExecError as e:
            raise errors.SanityCheckError("failed to run python --version.") from e
        if python_version_output != f"Python {self.EXPECTED_PYTHON_VERSION}\n":
            raise errors.SanityCheckError(f"unexpected python version: {python_version_output}")

    async def check_pip_version(self):
        """Checks that the pip version is the expected one.

        Raises:
            errors.SanityCheckError: Raised if the pip --version command could not be executed or if the outputted version is not the expected one.
        """
        try:
            pip_version_output: str = await self.container.with_exec(["pip", "--version"], skip_entrypoint=True).stdout()
        except dagger.ExecError as e:
            raise errors.SanityCheckError("failed to run pip --version.") from e
        if not pip_version_output.startswith(f"pip {self.EXPECTED_PIP_VERSION}"):
            raise errors.SanityCheckError(f"unexpected pip version: {pip_version_output}")

    async def check_time_zone(self):
        """We want to make sure that the system timezone is set to UTC.

        Raises:
            errors.SanityCheckError: Raised if the date command could not be executed or if the outputted timezone is not UTC.
        """
        try:
            tz_output: str = await self.container.with_exec(["date"], skip_entrypoint=True).stdout()
        except dagger.ExecError as e:
            raise errors.SanityCheckError("failed to run date.") from e
        if "UTC" not in tz_output:
            raise errors.SanityCheckError(f"unexpected timezone: {tz_output}")

    async def check_bash_is_installed(self):
        try:
            await self.container.with_exec(["bash", "--version"], skip_entrypoint=True).stdout()
        except dagger.ExecError as e:
            raise errors.SanityCheckError("failed to run bash --version.") from e


# DECLARE NEW BASE IMAGE VERSIONS BELOW THIS LINE
# Non breaking version should ideally inherit from the previous version.
# class _0_1_1(_0_1_0):

# Breaking version should inherit from AirbytePythonConnectorBaseImage.
# class _1_0_0(AirbyteConnectorBaseImage):


# HELPER FUNCTIONS
def get_all_python_base_images() -> dict[str, Type[AirbytePythonConnectorBaseImage]]:
    """Discover the base image versions declared in the module.
    It saves us from hardcoding the list of base images version: implementing a new class should be the only step to make a new base version available.

    Returns:
        dict[str, Type[AirbytePythonConnectorBaseImage]]: A dictionary of the base image versions declared in the module, keys are base image name and tag as string.
    """
    # Reverse the order of the members so that the latest version is first
    cls_members = reversed(inspect.getmembers(sys.modules[__name__], inspect.isclass))
    return {
        cls_member.name_with_tag: cls_member
        for _, cls_member in cls_members
        if issubclass(type(cls_member), type(AirbytePythonConnectorBaseImage))
        and cls_member != AirbytePythonConnectorBaseImage
        and cls_member != ABC
    }


ALL_BASE_IMAGES = get_all_python_base_images()