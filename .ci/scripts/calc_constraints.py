# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_container' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

import argparse
import fileinput
import urllib.request
import sys
from packaging.requirements import Requirement
from packaging.version import Version
import yaml


CORE_TEMPLATE_URL = "https://raw.githubusercontent.com/pulp/pulpcore/main/template_config.yml"


def fetch_pulpcore_upper_bound(requirement):
    with urllib.request.urlopen(CORE_TEMPLATE_URL) as f:
        template = yaml.safe_load(f.read())
    supported_versions = template["supported_release_branches"]
    supported_versions.append(template["latest_release_branch"])
    applicable_versions = sorted(
        requirement.specifier.filter((Version(v) for v in supported_versions))
    )
    if len(applicable_versions) == 0:
        raise Exception("No supported pulpcore version in required range.")
    return f"{requirement.name}~={applicable_versions[-1]}"


def split_comment(line):
    split_line = line.split("#", maxsplit=1)
    try:
        comment = "  # " + split_line[1].strip()
    except IndexError:
        comment = ""
    return split_line[0].strip(), comment


def to_upper_bound(req):
    try:
        requirement = Requirement(req)
    except ValueError:
        return f"# UNPARSABLE: {req}"
    else:
        if requirement.name == "pulpcore":
            # An exception to allow for pulpcore deprecation policy.
            return fetch_pulpcore_upper_bound(requirement)
        for spec in requirement.specifier:
            if spec.operator == "~=":
                return f"# NO BETTER CONSTRAINT: {req}"
            if spec.operator == "<=":
                operator = "=="
                max_version = spec.version
                return f"{requirement.name}{operator}{max_version}"
            if spec.operator == "<":
                operator = "~="
                version = Version(spec.version)
                if version.micro != 0:
                    max_version = f"{version.major}.{version.minor}.{version.micro-1}"
                elif version.minor != 0:
                    max_version = f"{version.major}.{version.minor-1}"
                elif version.major != 0:
                    max_version = f"{version.major-1}.0"
                else:
                    return f"# NO BETTER CONSTRAINT: {req}"
                return f"{requirement.name}{operator}{max_version}"
        return f"# NO UPPER BOUND: {req}"


def to_lower_bound(req):
    try:
        requirement = Requirement(req)
    except ValueError:
        return f"# UNPARSABLE: {req}"
    else:
        for spec in requirement.specifier:
            if spec.operator == ">=":
                if requirement.name == "pulpcore":
                    # Currently an exception to allow for pulpcore bugfix releases.
                    # TODO Semver libraries should be allowed too.
                    operator = "~="
                else:
                    operator = "=="
                min_version = spec.version
                return f"{requirement.name}{operator}{min_version}"
        return f"# NO LOWER BOUND: {req}"


def main():
    """Calculate constraints for the lower bound of dependencies where possible."""
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Calculate constraints for the lower or upper bound of dependencies where "
        "possible.",
    )
    parser.add_argument("-u", "--upper", action="store_true")
    parser.add_argument("filename", nargs="*")
    args = parser.parse_args()

    with fileinput.input(files=args.filename) as req_file:
        for line in req_file:
            if line.strip().startswith("#"):
                # Shortcut comment only lines
                print(line.strip())
            else:
                req, comment = split_comment(line)
                if args.upper:
                    new_req = to_upper_bound(req)
                else:
                    new_req = to_lower_bound(req)
                print(new_req + comment)


if __name__ == "__main__":
    main()
