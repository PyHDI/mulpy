from __future__ import absolute_import
from __future__ import print_function
import os
import sys

import veriloggen.core.vtypes as vtypes

class DataflowVariableConverter(object):
    def __init__(self):
        self.visited_node = {}

    def generic_visit(self, node):
        raise TypeError("Type '%s' is not supported." % str(type(node)))
    
    def visit(self, node):
        if node in self.visited_node:
            return self.visited_node[node]
        
        ret = self._visit(node)
        self.visited_node[node] = ret
        return ret
    
    def _visit(self, node):
        visitor = getattr(self, 'visit_' + node.__class__.__name__, self.generic_visit)
        return visitor(node)
