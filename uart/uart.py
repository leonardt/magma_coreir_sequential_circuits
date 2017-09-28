from magma import *
from mantle.coreir.logic import Not, And, Or
from mantle.coreir.compare import EQ
from mantle.coreir.arith import Add
from mantle.coreir.FF import FF

from magma import *
from magma.compatibility import IntegerTypes
from magma.bitutils import int2seq, seq2int
from collections import Sequence

#
# Create a column of n FFs initialized to init
#
# Each FF may have a ce, r, and s signal.
#
def FFs(n, init=0, has_ce=False, has_reset=False):
    if isinstance(init, IntegerTypes):
        init = int2seq(init, n)

    def f(y):
        return FF(init[y], has_ce=has_ce, has_reset=has_reset)

    return col(f, n)

## Register module name
def _RegisterName(name, n, init, ce, r):
    name += str(n)
    if ce: name += 'CE'
    if r:  name += 'R'

    if isinstance(init, Sequence):
         init = seq2int(init)
    if init is not 0: name += "_%04X" % init

    return name


@cache_definition
def DefineRegister(n, init=0, has_ce=False, has_reset=False, _type=Bits):
    """
    Generate an n-bit register
    Params
    ------
        `_type` - Bits, UInt, or SInt
    Interface
    ---------
        I : In(_type(n)), O : Out(_type(n))
    """
    if _type not in {Bits, UInt, SInt}:
        raise ValueError("Argument _type must be Bits, UInt, or SInt")
    T = _type(n)
    class _Register(Circuit):
        name = _RegisterName('Register', n, init, has_ce, has_reset)
        IO  = ['I', In(T), 'O', Out(T)] + ClockInterface(has_ce,has_reset)
        @classmethod
        def definition(reg):
            ffs = join(FFs(n, init, has_ce, has_reset))
            wire(reg.I, ffs.I)
            wire(ffs.O, reg.O)
            wireclock(reg, ffs)
    return _Register

def Register(n, init=0, has_ce=False, has_reset=False, **kwargs):
    return DefineRegister(n, init, has_ce, has_reset)(**kwargs)

__all__ = ['DefinePISO', 'PISO']


@cache_definition
def DeclareMux(height, width=None):
    if width is None:
        T = Bit
        coreir_name = "bitmux"
        coreir_genargs = {}
    else:
        T = Bits(width)
        coreir_name = "mux"
        coreir_genargs = {"width": width}
    return DeclareCircuit("coreir_mux".format(width),
                          'in0', In(T), 'in1', In(T),
                          'sel', In(Bit),
                          'out', Out(Bit),
                          coreir_name=coreir_name,
                          coreir_lib = "coreir",
                          coreir_genargs=coreir_genargs)

@cache_definition
def DefinePISO(n, init=0, has_ce=False, has_reset=False):

    T = Bits(n)
    class _PISO(Circuit):
        name = _RegisterName('PISO', n, init, has_ce, has_reset)
        IO = ['SI', In(Bit), 'PI', In(T), 'LOAD', In(Bit),
              'O', Out(Bit)] + ClockInterface(has_ce,has_reset)
        @classmethod
        def definition(piso):
            def mux2(y):
                return curry(DeclareMux(2)(), prefix='in')

            mux = braid(col(mux2, n), forkargs=['sel'])
            reg = Register(n, init, has_ce=has_ce, has_reset=has_reset)

            #si = array(*[piso.SI] + [reg.O[i] for i in range(n-1)])
            si = concat(array(piso.SI),reg.O[0:n-1])
            mux(si, piso.PI, piso.LOAD)
            reg(mux)
            wire(reg.O[n-1], piso.O)
            wireclock(piso, reg)

    return _PISO

def PISO(n, init=0, has_ce=False, has_reset=False, **kwargs):
    return DefinePISO(n, init, has_ce, has_reset)(**kwargs)


def _CounterName(name, n, ce, r):
    name += '%d' % n
    if ce: name += 'CE'
    if r:  name += 'R'
    return name

#
# Create an n-bit counter with a given increment.
#
# O : Out(UInt(n)), COUT : Out(Bit)
#
@cache_definition
def DefineCounter(n, cin=False, cout=True, incr=1, next=False,
    has_ce=False, has_reset=False):

    name = _CounterName('Counter', n, has_ce, has_reset)

    args = []
    if cin:
        args += ['CIN', In(Bit)]

    args += ["O", Out(UInt(n))]
    if cout:
        args += ["COUT", Out(Bit)]

    args += ClockInterface(has_ce, has_reset)

    Counter = DefineCircuit(name, *args)

    add = Add(n, cin=cin, cout=cout)
    reg = Register(n, has_ce=has_ce, has_reset=has_reset)

    wire( reg.O, add.I0 )
    wire( array(incr, n), add.I1 )

    reg(add.O)

    if next:
        wire( add.O, Counter.O )
    else:
        wire( reg.O, Counter.O )

    if cin:
        wire( Counter.CIN, add.CIN )

    if cout:
        wire( add.COUT, Counter.COUT )

    wireclock(Counter, reg)

    EndCircuit()

    return Counter

def Counter(n, cin=False, cout=True, incr=1, next=False,
             has_ce=False, has_reset=False, **kwargs):
    """Construct a n-bit up counter."""
    return DefineCounter(n, cin=cin, cout=cout, incr=incr, next=next,
               has_ce=has_ce, has_reset=has_reset)(**kwargs)

#
# Create an n-bit mod-m counter
#
@cache_definition
def DefineCounterModM(m, n, cin=False, cout=True, incr=1, next=False,
    has_ce=False):

    r = False
    s = False
    name = 'Counter(n={}, m={}, has_ce={}, r={}, s={})'.format(n, m, has_ce, r, s)

    args = []
    if cin:
        args += ['CIN', In(Bit)]

    args += ["O", Out(UInt(n))]
    if cout:
        args += ["COUT", Out(Bit)]

    args += ClockInterface(has_ce, r, s)

    CounterModM = DefineCircuit(name, *args)

    counter = Counter(n, cin=cin, cout=cout, incr=incr, next=next,
                   has_ce=has_ce, has_reset=True)
    reset = EQ(n)(counter.O, bits(m, n=n))

    if has_ce:
        CE = In(Bit)()
        reset = And(2)(reset, CE)
        # reset is sometimes called rollover or RO
        # note that we don't return RO in Counter

        # should also handle r in the definition

    wire(reset, counter.RESET) # synchronous reset

    if has_ce:
        wire(CE, counter.CE)

    if cin:
        wire( CounterModM.CIN, counter.CIN )

    wire( counter.O, CounterModM.O )

    if cout:
        wire( reset, CounterModM.COUT )

    wire(CounterModM.CLK, counter.CLK)
    if hasattr(counter,"CE"):
        wire(CounterModM.CE, counter.CE)

    EndCircuit()

    return CounterModM

def CounterModM(m, n, cin=False, cout=True, incr=1, next=False,
    has_ce=False, **kwargs):
    return DefineCounterModM(m, n, cin, cout, incr, next, has_ce)(**kwargs)
main = DefineCircuit('main', "tx", Out(Bit), "data", In(Bits(8)), "ready", Out(Bit),
                             "valid", In(Bit), "clk", In(Clock))

clock = CounterModM(103, 8)
baud = clock.COUT

count = Counter(4, has_ce=True, has_reset=True)
done = EQ(4)(count.O, bits(15, n=4))

run = FF(has_ce=True)
# run_n = LUT3([0,0,1,0, 1,0,1,0])
# run_n(done, main.valid, run)
run_n = And(2)(Or(2)(run, main.valid), Not()(done))
run(run_n)
wire(baud, run.CE)

# reset = LUT2(I0&~I1)(done, run)
reset = And(2)(done, Not()(run))
count(CE=baud, RESET=reset)

shift = PISO(9, has_ce=True)
# load = LUT2(I0 & ~I1)(valid,run)
load = And(2)(main.valid, Not()(run))
shift(1, concat(main.data, bits(0, n=1)), load)
wire(baud, shift.CE)

# ready = LUT2(~I0 & I1)(run, baud)
ready = And(2)(Not()(run), baud)

wire(ready, main.ready)
wire(shift, main.tx)

compile("uart", main, output="coreir")
