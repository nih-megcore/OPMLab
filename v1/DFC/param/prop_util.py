# Special property objects.

import os
from .prop import propObj

# --help

class Help(propObj):

    def msg2(self, s):
        "print a multiline string nicely"
        t = s.find('\n')
        while t > 0:
            print(f"{s[:t]}\n{'':29s}", end = '')
            s = s[t+1:]
            t = s.find('\n')
        print(s, end = '')

    def _set(self, p, val):
        print()
        print(p.usage)
        print("""\nOptions:
Parameter names (shown with '--' below) are also allowed in
parameter files (without the '--').\n""")

        for d in p.pList:
            name = d.get('name')
            if name[0] == '%':  # magic, don't show
                continue
            o = d.get('opt')
            a = d.get('arghelp')
            h = d.get('help')
            if o:
                if a:
                    s = f"--{name} {a}, -{o} {a}"
                else:
                    s = f"--{name}, -{o}"
            else:
                if a:
                    s = f"--{name} {a}"
                else:
                    s = f"--{name}"
            print(f"    {s:<25s}", end = '')
            if len(s) >= 25:
                print(f"\n{'':29s}", end = '')
            if h:
                self.msg2(h)
            if d.get('env'):
                print(f" [env_var = {d.get('env')}]", end = '')
            print()
        exit()

# %include file

class Include(propObj):

    def _set(self, p, val):
        args = self._getNargs(1, val)
        name = args[0]
        p.parseFile(name)

        ##fname = p.get('ParamFile')
        ## @@@ only if fname is relative
        ##dir = os.path.dirname(fname)
        ##param.parseFile(os.path.join(dir, args[0]))

