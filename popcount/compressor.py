#
# Implementation of compressor trees
#
from magma import fork, DefineCircuit, EndDefine, wire, In, Out, Bit, cache_definition
# from mantle import LUT2, LUT3, I0, I1, I2
from mantle.coreir.logic import XOr, Or, And

__all__ = ['compressor']

n3to2s = 0
@cache_definition
def DefineOp():
    Op = DefineCircuit("Op", "in0", In(Bit), "in1", In(Bit), "in2", In(Bit), "out", Out(Bit))
    a = And(2)(Op.in0, Op.in1)
    b = And(2)(Op.in1, Op.in2)
    c = And(2)(Op.in2, Op.in0)
    d = Or(3)(a, b, c)
    wire(d, Op.out)
    EndDefine()
    return Op

def compress3to2():
    global n3to2s
    n3to2s = n3to2s + 1
    Op = DefineOp()
    return fork([XOr(3), Op()])

# compress 2 and 3 bit groups in a column
def compresscolumn2(bits):
    n = len(bits)
    ones = []
    twos = []
    for i in range(0,n,3):
        if i+1 < n:
            c = compress3to2()
            c(bits[i], bits[i+1], 0 if i+2 >= n else bits[i+2])
            ones.append(c.out[0])
            twos.append(c.out[1])
        else:
            while i < n:
                ones.append(bits[i])
                i += 1
            break
    return twos, ones

# compress only 3 bit groups in a column
def compresscolumn3(bits):
    n = len(bits)
    ones = []
    twos = []
    for i in range(0,n,3):
        if i+2 < n:
            c = compress3to2()
            c(bits[i], bits[i+1], bits[i+2])
            ones.append(c.out[0])
            twos.append(c.out[1])
        else:
            while i < n:
                ones.append(bits[i])
                i += 1
            break
    return twos, ones


# compress only 3 bit groups in a column without ripple
def compress3(bits):
    res = []
    lasttwos = []
    for b in bits:
        twos, ones = compresscolumn3(b)
        res.append(ones + lasttwos)
        lasttwos = twos
    if len(lasttwos) > 0:
        res.append(lasttwos)
    return res

# ripple adder - assumes all the columns have at most 2 bits
def ripple(bits):
    res = []
    twos = []
    for b in bits:
        # ripple: combine last column of twos with this column
        b = b + twos
        # should only require fulladders (compress 3 to 2)
        assert len(b) <= 3
        twos, ones = compresscolumn2(b)
        res.append(ones)
    if len(twos) > 0:
        res.append(twos)
    return res


# returns True if there are any columns with more than 2 bits
def iscompressible(bits):
    for b in bits:
         if len(b) > 2:
             return True
    return False

def compressor(r):
    global n2to2s, n3to2s
    n3to2s = 0
    n2to2s = 0
    #print( list(map(len, r)) )
    while iscompressible(r):
        r = compress3(r)
        #print( list(map(len, r)) )
    r = ripple(r)
    #print( list(map(len, r)) )
    #print('n3to2s = {}'.format(n3to2s))
    return sum(r, [])

