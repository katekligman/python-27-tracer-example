import json
import inspect
from opcode import opmap
import sys

class TraceFunc():
    def __init__(self, frame):
        self.frame = frame
        # Set this right away in case the values are klobbered later on
        self.argsvalue = self.args
        self.exceptionvalue = None
        self.returnvalue = None

    @property    
    def args(self):
        args = {}
        names = self.frame.f_code.co_varnames[0:self.frame.f_code.co_argcount]
        for name in names:
            if name != 'self' and name != 'cls' and name in self.frame.f_locals:
                args[name] = str(self.frame.f_locals[name])
        return args
    
    @property
    def name(self):
        return self.frame.f_code.co_name        

    @property
    def lineinfo(self):
        info = inspect.getframeinfo(self.frame)
        return "%s %s %s" % (info.filename, info.lineno, info.function)

    @property
    def cls(self):    
        if 'self' in self.frame.f_locals:
            return self.frame.f_locals['self'].__class__.__name__
        elif 'cls' in self.frame.f_locals:
            return self.frame.f_locals['cls'].__name__
        else:    
            # static method or regular function
            # I should try using the signature to discover this
            return None
                 
    def exception(self, exceptionvalue = None):
        if exceptionvalue:
            self.exceptionvalue = exceptionvalue
        return self.exceptionvalue
        
    def returns(self, returnvalue = None):
        if returnvalue:
            self.returnvalue = str(returnvalue)
        return str(self.returnvalue)
    
    def to_dict(self):
        return {
            'name': self.name, 
            'args': self.argsvalue, 
            'class': self.cls, 
            'info': self.lineinfo, 
            'exception': str(self.exceptionvalue),
            'returns': str(self.returnvalue)
        }

frames = {}
def tracefunc(frame, event, arg):        
    if event not in ('call', 'exception', 'return'):
        return
        
    if frames is None:
        return        
                
    if event == 'call':
        frames[frame] = TraceFunc(frame)
    elif event == 'exception':
        frames[frame].exception(arg)
    elif event == 'return':    
        if frame not in frames:
            return
        # Opcode describing how the function returned. Used for detecting exceptions.
        op = frame.f_code.co_code[frame.f_lasti]
        if ord(op) not in (opmap['RETURN_VALUE'], opmap['YIELD_VALUE']):
            if frames[frame].exception() is None:
                frames[frame].exception(True)
        else:
            frames[frame].returns(arg)
            
        print(json.dumps(frames[frame].to_dict()))
        del frames[frame]
        
    return tracefunc

## Test functions and classes

def solofunc(arg1='default'):
    alocal = 'bob'

class MyClass():
    def __init__(self, one='defone', two='deftwo'):
        a = 'hello'
        
    @staticmethod
    def mystaticmethod():
        return 'mystaticmethod'
        
    @classmethod
    def myclassmethod(cls):
        return 'return a string saying myclassmethod'
        
    def throwsexception(self):
        a = 1 / 0
                
    def agenerator(self):
        yield 1

# Set the tracer -- 
# sys.settrace slower, logs exact excpetion info
# sys.setprofile faster, but can only log a bool for the exception field

sys.settrace(tracefunc)

solofunc()
a = MyClass()
a.mystaticmethod()
MyClass.mystaticmethod()
a.myclassmethod()
MyClass.myclassmethod()
a.agenerator()
try:
    a.throwsexception()
except:
    pass
