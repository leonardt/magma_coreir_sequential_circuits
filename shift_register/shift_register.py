from collections import Sequence
from magma import *
from magma.compatibility import IntegerTypes
from magma.bitutils import int2seq
from mantle.coreir.FF import FF


def DefineShiftRegister(width, has_enable=False, has_reset=False):
    class ShiftRegister(Circuit):
        name = "ShiftRegister(width={}, has_enable={}, has_reset={})".format(width, has_enable, has_reset)
        IO = ["I", In(Bit), "O", Out(Bit)] + ClockInterface(has_enable=has_enable, has_reset=has_reset)
        @classmethod
        def definition(io):
            ffs = [FF(has_ce=has_enable, has_reset=has_reset) for _ in range(width)]
            for ff in ffs:
                wireclock(io, ff)
                wiredefaultclock(io, ff)
            wire(io.I, ffs[0].I)
            fold(ffs, foldargs={"I":"O"})
            wire(ffs[-1].O, io.O)
    return ShiftRegister


def compile_shift_register(output_file, width, has_enable=False, has_reset=False):
    definition = DefineShiftRegister(width, has_enable, has_reset)
    compile(output_file, definition, output="coreir")


if __name__ == "__main__":
    compile_shift_register("shift_register_8_ce", 8, has_enable=True)
