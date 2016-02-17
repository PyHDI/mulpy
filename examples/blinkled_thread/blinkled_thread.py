from __future__ import absolute_import
from __future__ import print_function
import sys
import os

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mulpy import *
import veriloggen as vg

def mkBlinkled():
    m = Module('blinkled')
    led = m.Output('led', 8, initval=0)

    def blink(self):
        nonlocal led
        while True:
            led = 0
            for i in range(1024): pass
            led += 1

    m.thread(blink, args=())

    return m

def mkTest():
    m = vg.Module('test')
    
    # target instance
    led = mkBlinkled()
    
    # copy paras and ports
    params = m.copy_params(led)
    ports = m.copy_sim_ports(led)
    
    clk = ports['CLK']
    rst = ports['RST']
    
    uut = m.Instance(led, 'uut',
                     params=m.connect_params(led),
                     ports=m.connect_ports(led))
    
    vg.simulation.setup_waveform(m, uut, m.get_vars())
    vg.simulation.setup_clock(m, clk, hperiod=5)
    init = vg.simulation.setup_reset(m, rst, m.make_reset(), period=100)
    
    init.add(
        vg.Delay(1000 * 100),
        vg.Systask('finish'),
    )

    return m

if __name__ == '__main__':
    test = mkTest()
    verilog = test.to_verilog('tmp.v')
    #print(verilog)
    
    # run simulator (Icarus Verilog)
    sim = vg.simulation.Simulator(test)
    rslt = sim.run()
    print(rslt)
