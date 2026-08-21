__all__ = [
    "version_from_pypi_filename",
]

import packaging.version
import datetime

_pypi_upload_suffixes = (".bz2", ".tar", ".tar.bz2", ".tar.gz", ".tar.vz2", ".zip")


def version_from_pypi_filename(
    filename: str,
    package_name: str,
) -> packaging.version.Version | None:
    """
    Get the version of a release from the filename associated with a
    PyPI upload.

    If no valid version can be ascertained, return `None`.

    Raises
    ------
    packaging.version.InvalidVersion
        If the version is not valid.
    """
    package_name = package_name.lower()
    ver = filename.lower().strip()
    ver = ver.removeprefix(package_name)
    ver = ver.removeprefix(package_name.replace("-", "_"))
    ver = ver.removeprefix("-")

    for suffix in _pypi_upload_suffixes:
        ver = ver.removesuffix(suffix)
    ver = ver.split("-")[0]
    try:
        return packaging.version.Version(ver)
    except packaging.version.InvalidVersion:
        return None

