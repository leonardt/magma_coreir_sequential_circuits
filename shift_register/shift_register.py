from collections import Sequence
from magma import *
from magma.compatibility import IntegerTypes
from magma.bitutils import int2seq
from mantle.coreir.FF import FF


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


def DefineShiftRegister(height, width, has_enable=False, has_reset=False):
    T = Bits(width)
    class ShiftRegister(Circuit):
        name = "ShiftRegister(width={},has_enable={},has_reset={})".format(width, has_enable, has_reset)
        IO = ["I", In(T), "O", Out(T)] + ClockInterface(has_enable=has_enable, has_reset=has_reset)
        @classmethod
        def definition(io):
            regs = [Register(width, has_ce=has_enable, has_reset=has_reset) for _ in range(height)]
            wireclock(io, regs)
            wire(io.I, regs[0].I)
            fold(regs, foldargs={"I":"O"})
            wire(regs[0].O, io.O)
    return ShiftRegister


def compile_shift_register(output_file, width, has_enable=False, has_reset=False):
    definition = DefineShiftRegister(width, has_enable, has_reset)
    compile(output_file, definition, output="coreir")


if __name__ == "__main__":
    compile_shift_register("shift_register_8_ce", 8, has_enable=True)
