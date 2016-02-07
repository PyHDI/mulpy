from __future__ import absolute_import
from __future__ import print_function
import os
import sys
import copy

import veriloggen
import veriloggen.dataflow as dataflow

class Module(veriloggen.Module):
    """ Hardware Module class """
    def __init__(self, name=None, clock='CLK', reset='RST', tmp_prefix='_tmp'):
        veriloggen.Module.__init__(self, name, tmp_prefix)
        
        self.clock = self.Input(clock)
        self.reset = self.Input(reset)
        self._seq = veriloggen.Seq(self, 'seq', self.clock, self.reset)
        self._fsms = []
        
        self.cache = None

    #---------------------------------------------------------------------------
    def Comb(self, *statement):
        for s in statement:
            self.Assign(s)

    def Seq(self, *statement, **kwargs):
        self._seq.add(*statement, **kwargs)

    def FSM(self, name='fsm'):
        fsm = veriloggen.FSM(self, name, self.clock, self.reset)
        self._fsms.append(fsm)
        return fsm

    def Dataflow(self, *args):
        pass

    def Thread(self, func, args=()):
        pass

    #---------------------------------------------------------------------------
    def to_veriloggen_module(self):
        if self.cache:
            return self.cache

        self.resolve()
        
        self.cache = self
        return self
    
    def to_verilog(self, filename=None):
        obj = self.to_veriloggen_module()
        return veriloggen.Module.to_verilog(self, filename)

    #---------------------------------------------------------------------------
    def resolve(self):
        self._seq.make_always()
        for fsm in self._fsms:
            fsm.make_always()
