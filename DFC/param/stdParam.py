# This implements a default command line parser, which can also accept arguments
# from a set of parameter files and/or environment variables.

from .Param import Param
from .prop import *
from .prop_util import *

USAGE = "[options]"

# A standard set of parameters.

def getStdRegistry():
    "Return a registry of the common parameters that are always used"

    p = Param()

    p.mkDesc('help', 'h', Help(), help = "Show this help.")
    p.mkDesc('Verbose', 'v', Bool(), help = "Verbose output.")
    p.mkDesc('%include', None, Include())
    p.mkDesc('ParamFile', 'p', Filename(mustExist = True, ext = "param"),
                env = "param", arghelp = "PFILE",
                help = 'Parameter file name (optionally ending\nin ".param").')
    p.mkDesc('logName', None, Filename(), arghelp = "LOGFILE",
                help = "log messages to LOGFILE if Verbose is set.")
    return p

# Normally, you add more parameters from other registries to p.

def getParam(registry, pnames = None, /, usage = USAGE):
    """Create a Param() with standard and named parameters taken from
    the registry. If pnames is omitted, all names from the registry are
    added. Then parse the command line argument list, environment
    variables, and any named parameter file. The returned object p can
    be used to get the value of passed parameters via p.name."""

    # Create a standard parser, load any extra parameter descriptors,
    # and do the parse.

    p = Param()

    p.usage(usage)
    p.registryMerge(getStdRegistry())
    if pnames is None:
        p.registryMerge(registry)
    else:
        p.registerNames(pnames, registry)
    p.parseAll()

    return p
