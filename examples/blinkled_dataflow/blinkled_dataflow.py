from __future__ import absolute_import
from __future__ import print_function
import sys
import os

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mulpy import *

def mkBlinkled():
    m = Module('blinkled')
    clk = m.clock('CLK')
    rst = m.reset('RST')
    led = m.OutputReg('led', 8, initval=0)

    count = m.Reg('count', 32, initval=0)
    valid = m.Wire('valid')
    m.comb( valid(1) )
    
    _count = m.DataflowVar(count, valid, width=32)
    
    _p1 = _count + 1
    _p1m1 = _p1 - 1
    
    (p1, p1v), (p1m1, p1m1v) = m.dataflow(_p1, _p1m1, with_valid=True)
    
    m.seq( led.inc(), cond=p1==1024 )
    
    return m

if __name__ == '__main__':
    main = mkBlinkled()
    verilog = main.to_verilog('tmp.v')
    print(verilog)
