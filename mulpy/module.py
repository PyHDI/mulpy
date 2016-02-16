from __future__ import absolute_import
from __future__ import print_function
import os
import sys

import inspect
import ast
import types
import textwrap

import veriloggen
import veriloggen.core.vtypes as vtypes
import veriloggen.dataflow as dataflow
import veriloggen.dataflow.visitor as visitor

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
    def comb(self, *statement):
        for s in statement:
            self.Assign(s)

    def seq(self, *statement, **kwargs):
        self._seq.add(*statement, **kwargs)

    def fsm(self, name='fsm'):
        fsm = veriloggen.FSM(self, name, self.clock, self.reset)
        self._fsms.append(fsm)
        return fsm
    
    #---------------------------------------------------------------------------
    def DataflowVar(self, data, valid=None, ready=None, width=32, point=0, signed=False):
        tmp = None
        
        data_name = None
        if isinstance(data, vtypes._Variable):
            data_name = data.name
        else:
            if tmp is None: tmp = self.get_tmp()
            data_wire = self.Wire('inport%d_data' % tmp, width=width)
            self.comb( data_wire(data) )
            data_name = data_wire.name

        valid_name = None
        if valid is None:
            pass
        elif isinstance(valid, vtypes._Variable):
            valid_name = valid.name
        else:
            if tmp is None: tmp = self.get_tmp()
            valid_wire = self.Wire('inport%d_valid' % tmp)
            self.comb( valid_wire(valid) )
            valid_name = valid_wire.name
            
        ready_name = None
        if ready is None:
            pass
        elif isinstance(ready, vtypes._Variable):
            ready_name = ready.name
        else:
            if tmp is None: tmp = self.get_tmp()
            ready_wire = self.Wire('inport%d_ready' % tmp)
            self.comb( ready(ready_wire) )
            ready_name = ready_wire.name

        v = dataflow.Variable(data_name, valid_name, ready_name,
                              width=width, point=0, signed=signed)

        # remember RTL signal connectivity
        v.rtl_data = data
        v.rtl_valid = valid
        v.rtl_ready = ready
        
        return v
    
    def dataflow(self, *args, **kwargs):
        """ synthesize a dataflow module and create its instance """

        with_valid = kwargs['with_valid'] if 'with_valid' in kwargs else False
        with_ready = kwargs['with_ready'] if 'with_ready' in kwargs else False
        
        input_visitor = visitor.InputVisitor()
        input_vars = set()
        for arg in args:
            input_vars.update( input_visitor.visit(arg) )

        for arg in args:
            if arg.output_data is None:
                tmp = self.get_tmp()
                data = 'outport%d_data' % tmp
                valid = 'outport%d_valid' % tmp if with_valid else None
                ready = 'outport%d_ready' % tmp if with_ready else None
                arg.output(data, valid, ready)
            else:
                if with_valid and arg.output_valid is None:
                    #arg.output_valid = arg.output_data + '_valid'
                    raise ValueError('valid name must be specified when with_valid is enabled')
                if with_ready and arg.output_ready is None:
                    #arg.output_ready = arg.output_data + '_ready'
                    raise ValueError('ready name must be specified when with_ready is enabled')
                
        df = dataflow.Dataflow(*args)
        mod_name = "dataflow_module_%d" % self.get_tmp()
        mod = df.to_module(mod_name)

        inst_ports = []

        inst_ports.append( ('CLK', self.clock) )
        inst_ports.append( ('RST', self.reset) )
        
        for input_var in sorted(input_vars, key=lambda x:x.object_id):
            inst_ports.append( (input_var.input_data, input_var.rtl_data) )
            if input_var.input_valid is not None:
                inst_ports.append( (input_var.input_valid, input_var.rtl_valid) )
            if input_var.input_ready is not None:
                inst_ports.append( (input_var.input_ready, input_var.rtl_ready) )

        output_ports = []
                
        for arg in args:
            output_port_pair = []
            data = self.Wire(arg.output_data, width=arg.bit_length())
            inst_ports.append( (arg.output_data, data) )
            output_port_pair.append(data)
            if with_valid:
                valid = self.Wire(arg.output_valid)
                inst_ports.append( (arg.output_valid, valid) )
                output_port_pair.append(valid)
            if with_ready:
                ready = self.Wire(arg.output_ready)
                inst_ports.append( (arg.output_ready, ready) )
                output_port_pair.append(ready)
            elif arg.output_ready is not None:
                ready = vtypes.Int(1, width=1)
                inst_ports.append( (arg.output_ready, ready) )
                
            output_ports.append( tuple(output_port_pair) )

        self.Instance(mod, 'inst_' + mod_name, params=(), ports=inst_ports)

        return tuple(output_ports)
                
    #---------------------------------------------------------------------------
    def Thread(self, func, args=()):
        frame = inspect.currentframe()
        _locals = frame.f_back.f_locals
        _globals = frame.f_back.f_globals

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
