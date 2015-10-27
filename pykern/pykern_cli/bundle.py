# -*- coding: utf-8 -*-
u"""Build, promote, and deploy software bundles.

This module is an uber-package manager. It allows you to manage
software across package managers. It is not a replacement for a
package management system. This module uses yum, Mac
disks/packages/products, and Windows packages. Bundles are a means for
collecting packages and version them across operating system
boundaries.

The following definitions are sorted alphabetically and
self-referential so you may need to skip around:

bundle
    Collection of packages, other bundles, and/or individual files
    stored in a directory. Bundles are identified by a
    bundle_version.

bundle_channel
    A URI of the form name/os/machine/channel which points
    to (either as a symlink or redirect) to to a bundle_version.

bundle_class
    A URI of the form name/os/machine.

bundle_source
    The source directory or URI for the bundle. May be relative
    or absolute, depending on the context in which it is used.
    :func:`build` will go to the bundle_source to create a
    bundle.

bundle_version
    A URI of the form name/os/machine/version.

channel
    A level of testing for a sequence of bundle versions. The higher
    the channel the more testing and the lower the risk of
    failures. The channels are all pre-defined from lowest to highest
    level: develop, alpha, beta, and stable. At any given
    point in time, there is only one specific bundle assigned to a
    particular bundle_channel.

os_machine
    The operating system (usually, uname -s) and machine architecture
    (usually, uname -m) of the target separate by a forward slash (/),
    e.g. darwin-x86_64.

package
    Basic unit of software to be pushed to a target. It usually is
    a tarball, pkg, msi, etc., but may also be a directory of files. Packages
    have versions and architectures, but the file or directory is what
    identifies a package for bundling purposes.

promote
    The act of upgrading a bundle from one channel to the next higher
    channel. Bundles may not skip a channel.

repo
    The collections of bundles on a server. Repos are identified by a
    URI. It might be a dedicated server, e.g. pykern.us is the
    PyKern repo.

repo_base
    Root directory on the repo server, which holds the bundle_versions.

target
    The host on which the software will be installed. The target
    is a particular os_machine.

version
    Chronological id (yyyymmdd.hhmmss) for a bundle. Packages have
    versions, too, but these are arbitrary. For our purposes, a version
    only applies to a bundle. Any package's build date must not be newer
    than the version of the bundle in which it is contained.


:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

"""
#: Channels in order of decreasing risk
CHANNELS = ('develop', 'alpha', 'beta', 'stable')

cfg = config.register(
    repo_url='url',
    dest_dir='absolute_directory',
)

cfg.repo_url
cfg.dest_dir
"""

def build(bundle_source, repo_base):
    """Create a bundle from a configuration.

    Args:
        cmd (str or list): To be passed to subprocess to make the
            bundle file or directory. It will be passed the bundle
            version.

    Returns:
        str: build_version
    """
    # Looks for a command to build. How does it know the output?
    pass

def deposit(bundle_version):
    """Copy a build to a repository. The initial channel is always develop."""
    pass

def promote(bundle_channel):
    """Promote a bundle to the next bundle_channel."""
    pass
