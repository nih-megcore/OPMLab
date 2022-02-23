import os, sys
import logging
from time import asctime
from .prop import propObj

class Param(object):

    def __init__(self, progName = os.path.basename(sys.argv[0])):
        self.args = sys.argv[1:]
        self.pList = []         # parameter descriptors
        self.pnames = []        # just the names
        self.lowerp = []        # lowercase parameters names
        self.values = {}        # parameter value dict, indexed by the name
        self.opts = {}          # -X option flag descriptors
        self.env = {}           # environment variable names
        self.paramList = []     # names of all parameters that were specified
        self.aCopy = self.args  # used for logParam()

    def usage(self, msg, progName = os.path.basename(sys.argv[0])):
        "Set the usage (one line command syntax) message"
        self.progName = progName
        self.usage = f"Usage: {self.progName} {msg}"

    def msg(self, m, file = sys.stdout):
        "Print an informational message"
        print(f"{self.progName}: {m}", file = file)

    def err(self, m):
        "Print an error message and exit"
        self.msg(m, file = sys.stderr)
        sys.exit(1)

    # Create parameter descriptors.

    def mkDesc(self, name, opt, prop,
                listValue = False, arghelp = None, help = None,
                env = None, default = None):
        """Wrap up all a parameter's parameters into a descriptor and save it.
        The parameter's descriptor must still be registered before being used.

        Parameters:

            name : str

                Full parameter name, used in files and with --name on the command line.

            opt : str

                A single character, used as in -o on the command line. May be None.

            prop : propObj

                A property object. Property objects handle the parsing of the
                option arguments. Examples: Str(), Int(), Filename(), etc.

            listValue : bool

                When set, this option may be repeated, and new values are
                appended to a list, which is returned by self.get().

            arghelp : str

                A short (usually single word in all caps) description of the
                value of an option, used in the help message. Example: -d DIR.

            help : str

                A long description of the option. May contain \\n characters.

            env : str

                When set, this environment variable will be used as the value.

            default : arbitrary

                The default value of the option if it isn't otherwise specified.
        """

        if name.lower() in self.lowerp:
            self.err(f"attempt to register parameter {name} more than once")
        if opt is not None and self.opts.get(opt) is not None:
            self.err(f"attempt to register option -{opt} more than once")

        l = locals()
        desc = { k:v for k,v in l.items() if k != 'self' }
        self._addDesc(desc)
        return desc

    # The registry*() methods create "live" parameters from descriptors,
    # which have an associated property object.

    def register(self, name, opt, prop, **kw):
        "Create a descriptor (same as mkDesc()) and make it live"
        desc = self.mkDesc(name, opt, prop, **kw)
        self._activate(desc)

    def registryMerge(self, registry):
        "Add all the descriptors from registry (a Param) to self"
        for name in registry.pnames:
            self._addDesc(registry.getDesc(name), doProp = True)

    def registerNames(self, nList, registry):
        "Add just the named parameters from the registry to this parser"
        if type(nList) != list:
            raise Exception(f"not a list of names: {nList}")
        for name in nList:
            desc = registry.getDesc(name)
            if desc is None:
                raise Exception(f"unknown parameter name {name}")
            self._addDesc(desc, doProp = True)

    def _activate(self, desc):
        "Initialize the property object for this parameter"
        p = desc.get('prop')
        #if p is None:
        #    # a parameter with no prop just holds a default value
        #    d = desc.get('default')
        #    p = propObj(default = d)
        name = desc.get('name')
        p._setName(name)

    def _addDesc(self, desc, doProp = False):
        """Add this descriptor. Update the shortcut lists. When doProp
        is True, we'll add a property object to the class."""

        self.pList.append(desc)

        # key on some columns from the descriptor.
        name = desc['name']
        if name in self.pnames:
            self.err(f"attempt to register parameter {name} more than once")
        self.pnames.append(name)
        self.lowerp.append(name.lower())
        o = desc.get('opt')
        if o:
            self.opts[o] = desc
        e = desc.get('env')
        if e:
            self.env[e] = desc
        if doProp:
            self._activate(desc)

    def getDesc(self, name, warnUnk = False):
        "Return the descriptor for name, allowing case insensitive abbreviations"

        lname = name.lower()
        m = []
        for i, p in enumerate(self.lowerp):
            if p.startswith(lname):
                m.append(i)

        if len(m) > 1:
            self.err(f"Parameter '{name}' is ambiguous")
        if len(m) == 0:
            if warnUnk:
                self.msg(f"Warning, parameter {name} not recognized")
            return None

        return self.pList[m[0]]

    def getDescOpt(self, opt):
        "Find a parameter based on the opt"
        p = self.opts.get(opt)
        if p is None:
            print(f"option '-{opt}' is not recognized")
        return p

    def propset(self, p, args, **kw):
        "Set the parameter's property object"

        # returns the number of arguments consumed (from _set)

        prop = p['prop']
        name = p['name']        # index by canonical name
        if name[0] == '%':      # magic parameter (doesn't appear in help)
            return prop._set(self, args)

        if name not in self.paramList:
            self.paramList.append(name) # keep track of all specified parameters

        # If the parameter's value is already set, don't override, unless it's
        # a listValue, in which case it will append.

        oldval = self.values.get(name)
        if oldval is None or p['listValue']:
            if p['listValue']:
                return prop._set(self, args, **kw)
            return prop._set(self, args)

        return 0

    def do_help(self):
        p = self.getDesc('help')
        self.propset(p, [])     # setting causes the help message to be printed

    def get(self, name, default = None):
        "Get the value of a parameter"
        return self.values.get(name, default)

    def set(self, name, val):
        "Set the value of a parameter"
        # Don't update paramList
        self.values[name] = val

    def __getattr__(self, name):
        p = self.getDesc(name)
        if p is None:   # not a descriptor
            return None
        return self.values.get(name, p['default'])

    def parseArgs(self):
        "Parse the command line arguments"
        args = self.args

        while len(args):
            # get next arg
            a = args[0]

            # see if it looks like an option
            p = None
            if a[:2] == '--':
                name = a[2:]
                p = self.getDesc(name, warnUnk = True)
            elif a[:1] == '-':
                opt = a[1:]     # doesn't actually have to be one char
                p = self.getDescOpt(opt)

            if p:
                n = self.propset(p, args[1:], cmdLine=True) # all the rest of the args
                args = args[n+1:]   # remove the ones we used
            else:
                # stop processing the argument list if
                # we hit something that's not an option
                break

        # pass the rest of the args back up
        self.args = args

    def parseEnv(self):
        "Parse environment variables"
        # for all the parameters that can be set from the environment
        for name, p in self.env.items():
            s = os.environ.get(name)
            if s:
                self.propset(p, self.getValueList(s.split()))

    def parseFile(self, filename):
        "Read lines of the file, parse parameters"
        ll = open(filename).readlines()
        """ # is this needed for %include?
        try:
            ll = open(filename).readlines()
        except FileNotFoundError:
            try:
                ll = open(filename + ".param").readlines()
            except FileNotFoundError:
                self.err(f"File not found: {filename}")
        """
        for l in ll:
            # Ignore all past a '#'
            l = l.partition('#')[0].split()
            if len(l) == 0:
                continue

            # Parse a (name, argument list) pair.
            # Ignore unrecognized parameters.
            name = l.pop(0)
            args = self.getValueList(l)
            p = self.getDesc(name)
            if p:
                self.propset(p, args)   # ignore any extra args on the line

    def parseAll(self):
        """Parse the command line argument list, environment variables, and
        any named files."""

        # Parse the command line arguments and the environment variables.

        self.parseArgs()
        self.parseEnv()

        # Now any parameter file.

        pfile = self.get('ParamFile')
        if pfile is not None:
            self.parseFile(pfile)

    def getValue(self, x):
        # Return a single value, cast to int, float, or string (default)
        try:
            v = int(x)
        except ValueError:
            try:
                v = float(x)
            except ValueError:
                v = x
        return v

    def getValueList(self, l):
        return [self.getValue(x) for x in l]

    def logFile(self, name):
        "Set the log file name"
        self.logName = name

    def enableLogging(self):
        "Create a handler for the logging module that uses self.log()."
        logging.basicConfig(handlers = [loggingHandler(self)], level = 0)

    def log(self, s):
        """Print a log message, if Verbose is set. If self.logName has
        been set, the message will also be appended to the file."""

        if self.Verbose:
            print(s)
            if self.logName is not None:
                with open(self.logName, "a") as f:
                    print(s, file = f)

    def logParam(self, name = None, mode = "a"):
        "Append a list of all the parameters and their values to a logfile."

        # default name
        if name is None:
            name = self.logName
        if name is None:
            return

        with open(name, mode) as f:
            if mode == "a":
                print(file = f)
            print(asctime(), file = f)
            print(self.progName, end = ' ', file = f)
            for a in self.aCopy:
                print(a, end = ' ', file = f)
            print('\n***', file = f)
            for k in self.paramList:
                v = self.values[k]

                # if the propObj has a _print() method, use that
                prop = self.getDesc(k)['prop']
                if hasattr(prop, '_print'):
                    prop._print(k, v, file = f)
                else:
                    print(k, end = ' ', file = f)
                    if type(v) == tuple:
                        for x in v:
                            print(x, end = ' ', file = f)
                    else:
                        print(v, end = '', file = f)
                    print(file = f)
            print('***', file = f)

class loggingHandler(logging.Handler):

    def __init__(self, p):
        self.p = p
        self.setFormatter(
            logging.Formatter("%(filename)s:%(lineno)d %(levelname)s %(message)s"))
        self.setLevel(logging.DEBUG if p.Verbose else logging.ERROR)

    def handle(self, record):
        s = self.format(record)
        self.p.log(s)
