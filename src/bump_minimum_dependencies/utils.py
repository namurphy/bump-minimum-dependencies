__all__ = [
    "make_version_to_release_date_dict",
    "normalize_requirement_string",
    "version_from_pypi_filename",
]

import packaging.version
import datetime

_pypi_upload_suffixes = (".bz2", ".tar", ".tar.bz2", ".tar.gz", ".tar.vz2", ".zip")


def normalize_requirement_string(v: str | packaging.version.Version) -> str:
    """Remove trailing .0 suffixes and make it lower-case."""
    v = str(v).strip().lower().replace(".0,", ",")
    while v.endswith(".0"):
        v = v.removesuffix(".0")
    return v


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
        If the version specifier does not meet current standards.
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


def make_version_to_release_date_dict(
    response,
    skip_prerelease: bool = True,
    skip_yanked: bool = True,
) -> dict[packaging.version.Version, datetime.date]:
    """
    Take a response from a requests query and create a dict that maps
    Version objects to date objects for when they were released.

    Prereleases and yanked releases are excluded from the lists by
    default, as well as releases that use non-standard version specifiers.
    """
    version_to_release_dates: dict[packaging.version.Version, datetime.date] = {}

    for file in response["files"]:
        version = version_from_pypi_filename(
            filename=file["filename"],
            package_name=response["name"],
        )

        if version is None:
            continue

        if skip_prerelease and version.is_prerelease:
            continue

        if skip_yanked and file["yanked"]:
            continue

        date_string: str = file["upload-time"].split("T")[0]
        release_date: datetime.date = datetime.datetime.strptime(
            date_string, "%Y-%m-%d"
        ).date()

        if version not in version_to_release_dates:
            version_to_release_dates[version] = release_date
        else:
            version_to_release_dates[version] = min(
                version_to_release_dates[version], release_date
            )

    return version_to_release_dates
