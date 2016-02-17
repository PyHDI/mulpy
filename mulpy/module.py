from __future__ import absolute_import
from __future__ import print_function
import os
import sys

import collections

import inspect
import ast
import types
import textwrap

import veriloggen
import veriloggen.core.vtypes as vtypes
import veriloggen.dataflow as dataflow
import veriloggen.dataflow.visitor as visitor

class ClockDomain(object):
    def __init__(self, clock, reset=None):
        if (not isinstance(clock, vtypes._Variable) or
            isinstance(clock, vtypes._ParameterVairable)):
            raise TypeError('clock must be _Variable, not %s' % str(type(clock)))
        if reset is not None and (not isinstance(reset, vtypes._Variable) or
                                  isinstance(reset, vtypes._ParameterVairable)):
            raise TypeError('reset must be _Variable, not %s' % str(type(reset)))
        self.clock = clock
        self.reset = reset

    def __hash__(self):
        return hash( (id(self), id(self.clock), id(self.reset)) )

    def __eq__(self, other):
        return hash(self) == hash(other)

class Module(veriloggen.Module):
    """ Module class """
    def __init__(self, name=None, clock_name='CLK', reset_name='RST', tmp_prefix='_tmp'):
        veriloggen.Module.__init__(self, name, tmp_prefix)

        clock = self.Input(clock_name) if clock_name is not None else None
        reset = self.Input(reset_name) if reset_name is not None else None
        self.clock_domain = ClockDomain(clock, reset) if clock is not None else None
        
        self._seqs = collections.OrderedDict()
        self._fsms = []

    @property
    def clock(self):
        return self.clock_domain.clock

    @property
    def reset(self):
        return self.clock_domain.reset

    #---------------------------------------------------------------------------
    def comb(self, *statement):
        for s in statement:
            self.Assign(s)

    def seq(self, *statement, **kwargs):
        clock_domain = kwargs['clock_domain'] if 'clock_domain' in kwargs else self.clock_domain

        if clock_domain is None:
            raise ValueError('This Module has no clock domain.')

        if clock_domain not in self._seqs:
            self._seqs[clock_domain] = veriloggen.Seq(self, 'seq_' + clock_domain.clock.name,
                                                      clock_domain.clock,
                                                      clock_domain.reset)
            # call make_always method when the module is converted into verilog
            self.add_hook(self._seqs[clock_domain].make_always)
            
        self._seqs[clock_domain].add(*statement, **kwargs)

    def fsm(self, name='fsm', clock_domain=None):
        if clock_domain is None:
            clock_domain = self.clock_domain
        
        if clock_domain is None:
            raise ValueError('This Module has no clock domain.')

        fsm = veriloggen.FSM(self, name, clock_domain.clock, clock_domain.reset)
        self._fsms.append(fsm)
        # call make_always method when the module is converted into verilog
        self.add_hook(fsm.make_always)
        
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

        clock_domain = kwargs['clock_domain'] if 'clock_domain' in kwargs else self.clock_domain
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

        inst_ports.append( ('CLK', clock_domain.clock) )
        inst_ports.append( ('RST', clock_domain.reset) )
        
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
    def thread(self, func, args=()):
        frame = inspect.currentframe()
        _locals = frame.f_back.f_locals
        _globals = frame.f_back.f_globals

    #---------------------------------------------------------------------------
    def Instance(self, module, instname, params=None, ports=None):
        if not isinstance(module, Module): # when veriloggen.Module
            return veriloggen.Module.Instance(self, module, instname, params, ports)
        
        if ports is None:
            ports = []

        if isinstance(ports, dict):
            ports = [ (k, v) for k, v in ports.items() ]
        
        if module.clock_domain is None or self.clock_domain is None:
            pass
        elif len(ports) == 0:
            ports = [ (module.clock.name, self.clock),
                      (module.reset.name, self.reset) ]
        elif len(ports[0]) == 1: # without argument name
            ports.insert(0, self.reset)
            ports.insert(0, self.clock)
        else:
            ports.insert(0, (module.reset.name, self.reset))
            ports.insert(0, (module.clock.name, self.clock))
        
        return veriloggen.Module.Instance(self, module, instname, params, ports)
        
    #---------------------------------------------------------------------------
    def copy_ports(self, src, prefix=None, postfix=None, exclude=None):
        if not isinstance(src, Module): # when veriloggen.Module
            return veriloggen.Module.copy_ports(self, src, prefix, postfix, exclude)

        if src.clock_domain is None or self.clock_domain is None:
            return veriloggen.Module.copy_ports(self, src, prefix, postfix, exclude)
        
        if exclude is None:
            exclude = []

        exclude.append('^' + self.clock.name + '$')
        exclude.append('^' + self.reset.name + '$')
        
        return veriloggen.Module.copy_ports(self, src, prefix, postfix, exclude)
