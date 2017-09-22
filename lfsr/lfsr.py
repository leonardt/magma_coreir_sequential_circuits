from magma import *
from mantle.coreir import FF, XOr

@cache_definition
def DefineSIPO(n, init=0, has_ce=False, has_reset=False):
    """
    Generate Serial-In, Parallel-Out shift register.

    I : In(Bits(n),  O : Bits(n)
    """

    class _SIPO(Circuit):
        name = 'SIPO(n={}, init={}, has_ce={}, has_reset={})'.format(n, init,
                has_ce, has_reset)
        IO = ['I', In(Bit), 'O', Out(Bits(n))] + \
                ClockInterface(has_ce,has_reset)
        @classmethod
        def definition(sipo):
            ffs = [FF(init=init, has_ce=has_ce, has_reset=has_reset) for _ in range(n)]
            reg = scan(ffs, scanargs={"I":"O"})
            reg(sipo.I)
            wire(reg.O, sipo.O)
            wireclock(sipo, reg)
    return _SIPO

def SIPO(n, init=0, has_ce=False, has_reset=False, **kwargs):
    return DefineSIPO(n, init, has_ce, has_reset)(**kwargs)

_lfsrtaps = {}

def DefineLFSR(n, init=1, has_ce=False):
    circ = DefineCircuit("LFSR(n={}, init={}, has_ce={})".format(n, init, has_ce),
            "O", Out(Bits(n)), *ClockInterface(has_ce=has_ce))

    def readtaps():
        global _lfsrtaps

        if len(_lfsrtaps) != 0:
            return

        import csv

        name = os.path.join(os.path.dirname(__file__), 'lfsr.csv')

        f = open(name)
        row = csv.reader(f)

        for data in row:
            if data[0].isdigit():
                tap = int(data[0])
                _lfsrtaps[tap] = [int(v) for v in data[1].split(',')]

    readtaps()
    tap = _lfsrtaps[n]
    nt = len(tap)

    shift = SIPO(n, init=init, has_ce=has_ce)

    t = []
    for i in range(nt):
        t.append(shift.O[tap[i] - 1])
    t = array(t)

    s = uncurry(XOr(nt), prefix="in")(t)
    shift(s)

    wire(circ.O, shift.O)
    wireclock(circ, shift)
    wiredefaultclock(circ, shift)
    EndDefine()
    return circ

if __name__ == "__main__":
    definition = DefineLFSR(n=8)
    print(repr(definition))
    compile("lfsr", definition, output="coreir")
