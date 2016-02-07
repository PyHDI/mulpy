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

    def blink(self):
        nonlocal led
        while True:
            led = 0
            for i in range(1024): pass
            led += 1

    m.Thread(blink, args=())

    return m

if __name__ == '__main__':
    main = mkBlinkled()
    #vmod = main.to_veriloggen_module()
    verilog = main.to_verilog('tmp.v')
    print(verilog)
