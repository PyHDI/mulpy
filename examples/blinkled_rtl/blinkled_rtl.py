from __future__ import absolute_import
from __future__ import print_function
import sys
import os

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mulpy import *

def mkBlinkled():
    m = Module('blinkled')
    led = m.OutputReg('led', 8, initval=0)
    count = m.Reg('count', 10, initval=0)
    
    m.Seq( count.inc() )
    m.Seq( count(0), cond=count==1023 )
    m.Seq( led(led + 1), cond=count==1023 )

    return m

if __name__ == '__main__':
    main = mkBlinkled()
    verilog = main.to_verilog('tmp.v')
    print(verilog)
