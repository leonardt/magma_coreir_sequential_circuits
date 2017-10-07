from magma import *
import os
os.environ["MANTLE"] = "coreir"
from mantle.util.lfsr import DefineLFSR

definition = DefineLFSR(n=8)
print(repr(definition))
compile("lfsr", definition, output="coreir")
