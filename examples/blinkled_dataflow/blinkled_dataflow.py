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
    led = m.Output('led', 8, initval=0)

    count = m.Reg('count', 10, initval=0)

    def inc(v):
        nv = v + 1
        return nv

    nv = inc(count)
    next_count = m.Dataflow( nv )

    m.seq( led.inc(), cond=next_count==1024 )
    
    return m

if __name__ == '__main__':
    main = mkBlinkled()
    #vmod = main.to_veriloggen_module()
    verilog = main.to_verilog('tmp.v')
    print(verilog)
