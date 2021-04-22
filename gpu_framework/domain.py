"""
Definition of different domains
1. interval
2. disjunction of intervalss
3. octagon
4. zonotope
5. polyhedra

"""
from helper import *
from constants import *

import torch
import random
from torch.autograd import Variable
import torch.nn as nn
import torch.nn.functional as F
import time

import sys

# for check
def show_value(x):
    if not TEST:
        return 
    if isinstance(x, torch.Tensor):
        print('value', x.data.item())
    elif isinstance(x, Interval):
        print('interval', x.left.data.item(), x.righst.data.item())

def show_op(x):
    if not TEST:
        return 
    print(x + ':')


def handleNegative(interval):
    # print('interval', interval.left, interval.right)
    if interval.left.data.item() < 0.0:
        # print('check')
        if interval.left.data.item() == N_INFINITY.data.item():
            interval.left = var(0.0)
            interval.right = P_INFINITY
        else:
            # n = torch.floor_divide(var(-1.0).mul(interval.left), PI_TWICE)
            n = torch.ceil(var(-1.0).mul(interval.left).div(PI_TWICE))
            interval.left = interval.left.add(PI_TWICE.mul(n))
            interval.right = interval.right.add(PI_TWICE.mul(n))
    return interval

# interval domain

class Interval:
    def __init__(self, left=var(0.0), right=var(0.0)):
        self.left = left
        self.right = right
    
    # for the same api
    def getInterval(self):
        res = Interval()
        res.left = self.left
        res.right = self.right
        return res
    
    def setInterval(self, l, r):
        res = Interval()
        res.left = l
        res.right = r
        return res
    
    def new(self, left, right):
        return self.__class__(left, right)
    
    def in_other(self, other):
        return torch.logical_and(self.left >= other.left, self.right <= other.right)
    
    def clone(self):
        return self.new(self.left.clone(), self.right.clone())

    def getBox(self):
        return Box(self.getCenter(), self.getDelta())
    
    def getLength(self):
        if self.right.data.item() < self.left.data.item():
            return var(0.0)
        else:
            # print(f"in getLength: {self.right}, {self.left}")
            # print(f"in getLength: {self.right.sub(self.left)}")
            return torch.max(EPSILON, self.right.sub(self.left))
        
    def getVolumn(self):
        if self.right.data.item() < self.left.data.item():
            return var(0.0)
        else:
            return torch.max(EPSILON, (self.right.sub(self.left)))
    
    def split(self, partition):
        domain_list = list()
        unit = self.getVolumn().div(var(partition))
        for i in range(partition):
            new_domain = Interval()
            new_domain.left = self.left.add(var(i).mul(unit))
            new_domain.right = self.left.add(var(i + 1).mul(unit))
            domain_list.append(new_domain)
            # print('in split', new_domain.left, new_domain.right)
        return domain_list

    def getCenter(self):
        # C = var(2.0)
        return (self.left.add(self.right)).div(2.0)
    
    def getDelta(self):
        return (self.right.sub(self.left)).div(2.0)

    def equal(self, interval_2):
        if interval_2 is None:
            return False
        if interval_2.left.data.item() == self.left.data.item() and interval_2.right.data.item() == self.right.data.item():
            return True
        else:
            return False

    def isEmpty(self):
        # print(self.right, self.left)
        # print(f"judge empty: {self.left.data.item(), self.right.data.item()}")
        if self.right.data.item() < self.left.data.item():
            return True
        else:
            return False
    
    def isPoint(self):
        if self.right.data.item() == self.left.data.item(): # or abs(self.right.data.item() - self.left.data.item()) < EPSILON.data.item():
            return True
        else:
            return False

    def setValue(self, x):
        res = Interval()
        res.left = x
        res.right = x
        return res
    
    def soundJoin(self, other):
        # if debug:
        #     r = torch.cuda.memory_reserved(0) 
        #     a = torch.cuda.memory_allocated(0)
        #     print(f"soundJoin, before, cuda memory reserved: {r}, allocated: {a}")
        res = self.new(torch.min(self.left, other.left), torch.max(self.right, other.right))
        # if debug:
        #     r = torch.cuda.memory_reserved(0) 
        #     a = torch.cuda.memory_allocated(0)
        #     print(f"soundJoin, after cuda memory reserved: {r}, allocated: {a}")
        return res
    
    def getZonotope(self):
        res = Zonotope()
        res.center = (self.left.add(self.right)).div(var(2.0))
        res.alpha_i[0] = (self.right.sub(self.left)).div(var(2.0))
        return res
    
    # arithmetic
    def add(self, y):
        # self + y
        show_op('add')
        show_value(self)
        show_value(y)

        res = Interval()
        if isinstance(y, torch.Tensor):
            res.left = self.left.add(y)
            res.right = self.right.add(y)
        else:
            # print(res.left, y.left)
            res.left = self.left.add(y.left)
            res.right = self.right.add(y.right)

        show_value(res)
        return res

    def sub_l(self, y):
        # self - y
        show_op('sub_l')
        show_value(self)
        show_value(y)

        res = Interval()
        if isinstance(y, torch.Tensor):
            res.left = self.left.sub(y)
            res.right = self.right.sub(y)
        else:
            res.left = self.left.sub(y.right)
            res.right = self.right.sub(y.left)
        
        show_value(res)
        # if debug:
        #     print(f"#sub_l# size of res:  {sys.getsizeof(res), sys.getsizeof(res.left), sys.getsizeof(res.right)}")
        
        return res

    def sub_r(self, y):
        # y - self
        show_op('sub_r')
        show_value(y)
        show_value(self)
        
        res = Interval()
        if isinstance(y, torch.Tensor):
            res.left = y.sub(var(1.0).mul(self.right))
            res.right = y.sub(var(1.0).mul(self.left))
        else:
            res.left = y.left.sub(self.right)
            res.right = y.right.sub(self.left)
        
        show_value(res)
        # if debug:
        #     print(f"#sub_r# size of res:  {sys.getsizeof(res), sys.getsizeof(res.left), sys.getsizeof(res.right)}")
        return res

    def mul(self, y):
        # self * y
        # show_op('mul')
        # show_value(y)
        # show_value(self)
        # if debug:
        #     r1 = torch.cuda.memory_reserved(0) 
        #     a1 = torch.cuda.memory_allocated(0)
        #     print(f"#interval mul, ini#, memory: {a1}")
        #     print(f"in interval mul: self:{self.left, self.right}")
        #     print(f"in interval mul: y:{y}")

        res = Interval()
        # if debug:
        #     r2 = torch.cuda.memory_reserved(0) 
        #     a2 = torch.cuda.memory_allocated(0)
        #     print(f"#interval mul, ini Interval()#, memory: {a2}, {a2-a1}")
        if isinstance(y, torch.Tensor):
            # print(f"size of l, r of  res.left: {get_size(self.right.mul(y))},  {get_size(self.left.mul(y))}")
            res.left = torch.min(self.right.mul(y), self.left.mul(y))
            # res.left = torch.min(self.right.mul(y), self.left.mul(y))
            # tmp = self.right.mul(y)
            # if debug:
            #     a3 = torch.cuda.memory_allocated(0)
            #     print(f"#interval mul, res.left: {res.left}#, memory: {a3}, {a3-a1}")
            res.right = torch.max(self.right.mul(y), self.left.mul(y))
            # if debug:
            #     a4 = torch.cuda.memory_allocated(0)
            #     print(f"#interval mul, res.right: {res.right}#, memory: {a4}, {a4-a1}")
        else:
            res.left = torch.min(torch.min(y.left.mul(self.left), y.left.mul(self.right)), torch.min(y.right.mul(self.left), y.right.mul(self.right)))
            # if debug:
            #     a3 = torch.cuda.memory_allocated(0)
            #     print(f"#interval mul, res.left: {res.left}#, memory: {a3}, {a3-a1}")
            res.right = torch.max(torch.max(y.left.mul(self.left), y.left.mul(self.right)), torch.max(y.right.mul(self.left), y.right.mul(self.right)))
            # if debug:
            #     a4 = torch.cuda.memory_allocated(0)
                # print(f"#interval mul, res.right: {res.right}#, memory: {a4}, {a4-a1}")
        show_value(res)
        # if debug:
        #     print(f"#mul# size of res:  {get_size(res.left), get_size(res.right)}")
        #     exit(0)
        return res

    def div(self, y):
        # y/self
        # 1. tmp = 1/self 2. res = tmp * y
        show_op('div')
        show_value(y)
        show_value(self)

        res = Interval()
        tmp_interval = Interval()
        tmp_interval.left = var(1.0).div(self.right)
        tmp_interval.right = var(1.0).div(self.left)
        res = tmp_interval.mul(y)
        
        show_value(res)
        return res

    def exp(self):
        show_op('exp')
        show_value(self)

        # print(f'DEGUB:, exp', self.left, self.right)

        res = Interval()
        res.left = torch.exp(self.left)
        res.right = torch.exp(self.right)

        show_value(res)
        return res

    def cos(self):
        # show_op('cos')
        # show_value(self)
        
        # res = Interval()
        # if debug:
        #     r1 = torch.cuda.memory_reserved(0) 
        #     a1 = torch.cuda.memory_allocated(0)
        #     print(f"#interval cos, ini#, memory: {a1}")

        cache = Interval()
        cache.left = self.left
        cache.right = self.right
        # if debug:
        #     r5 = torch.cuda.memory_reserved(0) 
        #     a5 = torch.cuda.memory_allocated(0)
        #     print(f"#interval cos, before handleNeg#, memory: {a5}, {a5-a1}")

        cache = handleNegative(cache)
        # if debug:
        #     r6 = torch.cuda.memory_reserved(0) 
        #     a6 = torch.cuda.memory_allocated(0)
        #     print(f"#interval cos, after handleNeg#, memory: {a6}, {a6-a1}")
        # print('y_neg', cache.left, cache.right)
        # n = torch.floor_divide(cache.left, PI_TWICE)
        # t = cache.sub_l(PI_TWICE.mul(n))
        t = cache.fmod(PI_TWICE)
        # print('t', t.left, t.right)
        # if debug:
        #     r2 = torch.cuda.memory_reserved(0) 
        #     a2 = torch.cuda.memory_allocated(0)
        #     print(f"#interval cos, middle#, memory: {a2}, {a2 - a1}")
        # print(type(t.getVolumn()), type(PI_TWICE))
        if t.getVolumn().data.item() >= PI_TWICE.data.item():
            # print('volume', t.getVolumn())
            res = Interval(var_list([-1.0]), var_list([1.0]))
            # show_value(res)
            # return res
        # when t.left > PI same as -cos(t-pi)
        elif t.left.data.item() >= PI.data.item():
            # if debug:
            #     r7 = torch.cuda.memory_reserved(0) 
            #     a7 = torch.cuda.memory_allocated(0)
            #     print(f"#interval cos, before cosv#, memory: {a7}, {a7 - a1}")
            cosv = (t.sub_l(PI)).cos()
            # if debug:
            #     r8 = torch.cuda.memory_reserved(0) 
            #     a8 = torch.cuda.memory_allocated(0)
            #     print(f"#interval cos, after cosv#, memory: {a8}, {a8 - a1}")
            res = cosv.mul(var_list([-1.0]))
            # show_value(res)
            # return res
        else:
            tl = torch.cos(t.right)
            tr = torch.cos(t.left)
            if t.right.data.item() <= PI.data.item():
                # res.left = tl
                # res.right = tr
                res = Interval(tl, tr)
                # show_value(res)
                # return res
            elif t.right.data.item() <= PI_TWICE.data.item():
                # res.left = var(-1.0)
                # res.right = torch.max(tl, tr)
                res = Interval(var_list([-1.0]), torch.max(tl, tr))
                # show_value(res)
                # return res
            else:
                # res.left = var(-1.0)
                # res.right = var(1.0)
                res = Interval(var_list([-1.0]), var_list([1.0]))
                # show_value(res)
                # return res
        # if debug:
        #     r3 = torch.cuda.memory_reserved(0) 
        #     a3 = torch.cuda.memory_allocated(0)
        #     print(f"#interval cos, end#, memory: {a3}, {a3 - a1}")
        return res

    def sin(self):
        return self.sub_l(PI_HALF).cos()

    def max(self, y):
        res = Interval()
        if isinstance(y, torch.Tensor):
            res.left = torch.max(self.left, y)
            res.right = torch.max(self.right, y)
        else:
            res.left = torch.max(self.left, y.left)
            res.right = torch.max(self.right, y.right)
        return res
    
    def min(self, y):
        res = Interval()
        if isinstance(y, torch.Tensor):
            res.left = torch.min(self.left, y)
            res.right = torch.min(self.right, y)
        else:
            res.left = torch.min(self.left, y.left)
            res.right = torch.min(self.right, y.right)
        return res
    
    def sqrt(self):
        res = Interval()
        res.left = torch.sqrt(self.left)
        res.right = torch.sqrt(self.right)
        return res
    
    def fmod(self, y):
        # y is PI2
        # if debug:
        #     r1 = torch.cuda.memory_reserved(0) 
        #     a1 = torch.cuda.memory_allocated(0)
        #     print(f"#interval fmod, ini#, memory: {a1}")

        if isinstance(y, torch.Tensor):
            y_interval = Interval()
            y_interval = y_interval.setValue(y)
            # if debug:
            #     r2 = torch.cuda.memory_reserved(0) 
            #     a2 = torch.cuda.memory_allocated(0)
            #     print(f"#interval fmod, setValue(Tensor)#, memory: {a2}, {a2 - a1}")
        else:
            y_interval = y
            # if debug:
            #     r2 = torch.cuda.memory_reserved(0) 
            #     a2 = torch.cuda.memory_allocated(0)
            #     print(f"#interval fmod, setValue(Interval)#, memory: {a2}, {a2 - a1}")
        
        if self.left.data.item() < 0.0:
            yb = y_interval.left
        else:
            yb = y_interval.right
        
        # if debug:
        #     r3 = torch.cuda.memory_reserved(0) 
        #     a3 = torch.cuda.memory_allocated(0)
        #     print(f"#interval fmod, after self.left#, memory: {a3}, {a3 - a1}")
        # # print('self left', self.left)
        # print('yb', yb)
        n = self.left.div(yb)
        # if debug:
        #     r4 = torch.cuda.memory_reserved(0) 
        #     a4 = torch.cuda.memory_allocated(0)
        #     print(f"#interval fmod, div#, memory: {a4}, {a4 - a1}")
        if(n.data.item() <= 0.0): 
            n = torch.ceil(n)
            # if debug:
            #     r5 = torch.cuda.memory_reserved(0) 
            #     a5 = torch.cuda.memory_allocated(0)
            #     print(f"#interval fmod, ceil#, memory: {a5}, {a5 - a1}")
        else:
            n = torch.floor(n)
            # if debug:
            #     r6 = torch.cuda.memory_reserved(0) 
            #     a6 = torch.cuda.memory_allocated(0)
            #     print(f"#interval fmod, floor#, memory: {a6}, {a6 - a1}")
        # print('n', n)

        # n_interval = Interval()
        # n_interval = n_interval.setValue(n)

        # if debug:
        #     r7 = torch.cuda.memory_reserved(0) 
        #     a7 = torch.cuda.memory_allocated(0)
        #     print(f"#interval fmod, new n interval#, memory: {a7}, {a7 - a1}")
        # print(self.left, self.right)
        # print(y_interval.mul(n_interval).left, y_interval.mul(n_interval).right)
        tmp_1 = y_interval.mul(n)
        # if debug:
        #     r9 = torch.cuda.memory_reserved(0) 
        #     a9 = torch.cuda.memory_allocated(0)
        #     print(tmp_1.left, tmp_1.right)
        #     print(f"#interval fmod, mul#, memory: {a9}, {a9 - a1}")
        # res = self.sub_l(y_interval.mul(n))
        res = self.sub_l(tmp_1)
        # if debug:
        #     r8 = torch.cuda.memory_reserved(0) 
        #     a8 = torch.cuda.memory_allocated(0)
        #     print(res.left, res.right)
        #     print(f"size of res: {sys.getsizeof(res)}")
        #     print(f"#interval fmod, sub #, memory: {a8}, {a8 - a1}")
        
        return res


class Box():
    def __init__(self, c, delta):
        self.c = c
        self.delta = delta
    
    def new(self, c, delta):
        # if debug:
        #     a1 = torch.cuda.memory_allocated(0)
        res = self.__class__(c, delta)
        # if debug:
        #     a2 = torch.cuda.memory_allocated(0)
        #     print(f"new box: memory cost: {a2 - a1}")
        return res
    
    def clone(self):
        return self.new(self.c.clone(), self.delta.clone())
    
    def check_in(self, other):
        # check: other in self (other.left >= self.left and other.right <= self.right)
        self_left = self.c - self.delta
        self_right = self.c + self.delta
        other_left = other.c - other.delta
        other_right = other.c + other.delta
        
        left_cmp = torch.ge(other_left, self_left)
        if False in left_cmp:
            return False
        right_cmp = torch.ge(self_right, other_right)
        if False in right_cmp:
            return False
        return True
    
    def select_from_index(self, dim, idx):
        return self.new(torch.index_select(self.c, dim, idx), torch.index_select(self.delta, dim, idx))

    def set_from_index(self, idx, other):
        # print(f"c: {self.c}, idx:{idx}")
        # print(f"c[idx]: {self.c[idx]}, other: {other.c, other.delta}")
        self.c[idx] = other.c
        self.delta[idx] = other.delta
        # print(f"c: {self.c}")
        return 
    
    def set_value(self, value):
        # print(f"value: {value}")
        return self.new(value, var(0.0))
    
    def sound_join(self, other):
        l1, r1 = self.c - self.delta, self.c + self.delta
        l2, r2 = other.c - other.delta, other.c + other.delta
        l = torch.min(l1, l2)
        r = torch.max(r1, r2)
        # if debug:
        #     r = torch.cuda.memory_reserved(0) 
        #     a = torch.cuda.memory_allocated(0)
        #     print(f"box sound_join, before, cuda memory reserved: {r}, allocated: {a}")
        res = self.new((r + l) / 2, (r - l) / 2)
        # if debug:
        #     r = torch.cuda.memory_reserved(0) 
        #     a = torch.cuda.memory_allocated(0)
        #     print(f"box sound_join, after, cuda memory reserved: {r}, allocated: {a}")
        return res
        
    def getRight(self):
        return self.c.add(self.delta)
    
    def getLeft(self):
        return self.c.sub(self.delta)
    
    def getInterval(self):
        res = Interval(self.c.sub(self.delta), self.c.add(self.delta))
        return res
    
    def matmul(self, other):
        return self.new(self.c.matmul(other), self.delta.matmul(other.abs()))
    
    def add(self, other):
        #TODO:
        # if debug:
        #     r1 = torch.cuda.memory_reserved(0) 
        #     a1 = torch.cuda.memory_allocated(0)
        #     print(f"#add, ini#, memory: {a1}")
        if isinstance(other, torch.Tensor):
            c, d = self.c.add(other), self.delta
            # if debug:
            #     r3 = torch.cuda.memory_reserved(0) 
            #     a3 = torch.cuda.memory_allocated(0)
                # print(f"#add, c, d# : memory cost {a3}, {a3 - a1}")
            res = self.new(c, d)
            # if debug:
            #     r4 = torch.cuda.memory_reserved(0) 
            #     a4 = torch.cuda.memory_allocated(0)
            #     print(f"#add, res new# : memory cost {a4}, {a4 - a1}")
            # res = self.new(self.c.add(other), self.delta)
        else:
            c, d = self.c.add(other.c), self.delta + other.delta
            # if debug:
            #     r3 = torch.cuda.memory_reserved(0) 
            #     a3 = torch.cuda.memory_allocated(0)
            #     print(f"#add, c, d# : memory cost {a3}, {a3 - a1}")
            res = self.new(c, d)
            # if debug:
            #     r4 = torch.cuda.memory_reserved(0) 
            #     a4 = torch.cuda.memory_allocated(0)
            #     print(f"#add, res new# : memory cost {a4}, {a4 - a1}")
            # res = self.new(self.c.add(other.c), self.delta + other.delta)
        # if debug:
        #     r2 = torch.cuda.memory_reserved(0) 
        #     a2 = torch.cuda.memory_allocated(0)
        #     print(f"#add# : memory cost {a2}, {a2 - a1}")
        return res
            
    def sub_l(self, other): # self - other
        # print(f"sub_l other:{other}")
        if isinstance(other, torch.Tensor):
            return self.new(self.c.sub(other), self.delta)
        else:
            # print(f"in here")
            # print(f"self.c: {self.c}")
            # print(f"other.c: {other.c}")
            return self.new(self.c.sub(other.c), self.delta + other.delta)
    
    def sub_r(self, other): # other - self
        if isinstance(other, torch.Tensor):
            return self.new(other.sub(self.c), self.delta)
        else:
            return self.new(other.c.sub(self.c), self.delta + other.delta)
    
    def mul(self, other):
        # if debug:
        #     r1 = torch.cuda.memory_reserved(0) 
        #     a1 = torch.cuda.memory_allocated(0)
        #     print(f"#mul ini# : memory cost {a1}")
        # print(f"mul, {self.c.shape}")
        interval = self.getInterval()
        if isinstance(other, torch.Tensor):
            pass
        else:
            other = other.getInterval()
        res_interval = interval.mul(other)
        res = res_interval.getBox()
        # print(f"mul, {res.c.shape}")
        # if debug:
        #     r2 = torch.cuda.memory_reserved(0) 
        #     a2 = torch.cuda.memory_allocated(0)
        #     print(f"#mul# : memory cost {a2}, {a2 - a1}")
        #     del res_interval
        #     del interval
        #     a3 = torch.cuda.memory_allocated(0)
        #     print(f"after del in mul: {a3}, {a3 - a1}")
        return res
    
    def cos(self):
        #TODO: only for box, not for zonotope
        # if debug:
        #     r1 = torch.cuda.memory_reserved(0) 
        #     a1 = torch.cuda.memory_allocated(0)
        #     print(f"#cos ini# : memory cost {a1}")
        # For batch:
        B = self.c.shape[0]
        # print(self.c.shape)
        # print(self.c)
        if B > 1:
            c, delta = torch.tensor([]), torch.tensor([])
            for i in range(B):
                new_c, new_delta = self.c[i], self.delta[i]
                new_box = self.new(new_c, new_delta)
                interval = new_box.getInterval()
                res_interval = interval.cos()
                get_box = res_interval.getBox()
                # print(c)
                if c.shape[0] == 0:
                    c, delta = get_box.c, get_box.delta
                else:
                    # print(c.shape, get_box.c.shape, delta.shape, get_box.delta.shape)
                    #TODO
                    # print('be', get_box.c.shape, c.shape)
                    if len(get_box.c.shape) != len(c.shape) and len(c.shape) >= 1:
                        get_box.c, get_box.delta = get_box.c.unsqueeze(0), get_box.delta.unsqueeze(0)
                    # print('mid', get_box.c.shape, c.shape)
                    c, delta = torch.cat((c, get_box.c), 0), torch.cat((delta, get_box.delta), 0)
                    # print('after', get_box.c.shape, c.shape)
            # print(f"cos, {c.shape}")
            if len(c.shape) == 1:
                c, delta = c.unsqueeze(1), delta.unsqueeze(1)
            return self.new(c, delta)
        else:
            # TODO: support batch and double check
            interval = self.getInterval()
            res_interval = interval.cos()
            res = res_interval.getBox()
            return res
        # if debug:
        #     r2 = torch.cuda.memory_reserved(0) 
        #     a2 = torch.cuda.memory_allocated(0)
        #     print(f"#cos# : memory cost {a2}, {a2 - a1}")
        #     del res_interval
        #     del interval
        #     a3 = torch.cuda.memory_allocated(0)
        #     print(f"after del in cos: {a3}, {a3 - a1}")
        # return res
    
    def exp(self):
        a = self.delta.exp()
        b = (-self.delta).exp()
        return self.new(self.c.exp().mul((a+b)/2), self.c.exp().mul((a-b)/2))
    
    def div(self, other): # other / self
        interval = self.getInterval()
        res_interval = interval.div(other)
        return res_interval.getBox()
    
    def sigmoid(self): # monotonic function
        tp = torch.sigmoid(self.c + self.delta)
        bt = torch.sigmoid(self.c - self.delta)
        # print(f"in sigmoid, tp: {tp}, bt: {bt}")
        return self.new((tp + bt)/2, (tp - bt)/2)
    
    def tanh(self): # monotonic function
        tp = torch.tanh(self.c + self.delta)
        bt = torch.tanh(self.c - self.delta)
        return self.new((tp + bt)/2, (tp - bt)/2)
    
    def relu(self): # monotonic function
        # relu_time = time.time()
        tp = F.relu(self.c + self.delta)
        bt = F.relu(self.c - self.delta)
        # print(f"relu: {time.time() - relu_time}")

        # approximate volume
        p0 = var(1.0)
        # for idx, c in enumerate(self.c):
        #     delta = self.delta[idx]
        #     if (c + delta) > 0.0 and (c - delta).data.item() < 0.0:
        #         p0 = p0.mul((c+delta) * 1.0/(delta * 2.0))
        # print(f"after volume  approximation: {time.time() - relu_time}")
        
        return self.new((tp + bt)/2, (tp - bt)/2)
    
    def sigmoid_linear(self, sig_range):
        # sl_time = time.time()
        a = var(0.5/sig_range)
        b = var(0.5)
        x = self.mul(a).add(b)
        tp = torch.clamp(x.c + x.delta, 0, 1)
        bt = torch.clamp(x.c - x.delta, 0, 1)
        # print(f"sl: {time.time() - sl_time}")

        # approximate volume
        p0 = var(1.0)
        # for idx, c in enumerate(self.c):
        #     delta = self.delta[idx]
        #     if delta.data.item() > 0.0:
        #         r = torch.clamp(c + delta, 0, 1)
        #         l = torch.clamp(c - delta, 0, 1)
        #         p0 = p0.mul((r - l) * 1.0/ (delta  * 2.0))
        # print(f"after volume  approximation: {time.time() - sl_time}")

        return self.new((tp + bt)/2, (tp - bt)/2)


class Zonotope:
    def __init__(self, left=0.0, right=0.0):
        self.center = var((left + right)/2.0)
        self.alpha_i = list([var((right - left)/2.0)])

    def getInterval(self):
        # print('c, alpha0', self.center, self.alpha_i)
        l = self.center
        r = self.center
        for i in self.alpha_i:
            l = l.sub(torch.abs(i))
            r = r.add(torch.abs(i))
        
        interval = Interval()
        interval.left = l
        interval.right = r
        # print('-------end c, alpha0', self.center, self.alpha_i[0])
        # print('----====l, r', l, r)
        return interval
    
    def getIntervalLength(self):
        interval = self.getInterval()
        return interval.getVolumn()

    def getLength(self):
        return self.getIntervalLength()

    def getVolumn(self):
        return self.getIntervalLength()
    
    def split(self, partition):
        domain_list = list()
        tmp_self = self.getInterval()
        unit = tmp_self.getVolumn().div(var(partition))
        for i in range(partition):
            new_domain = Interval()
            new_domain.left = tmp_self.left.add(var(i).mul(unit))
            new_domain.right = tmp_self.left.add(var(i + 1).mul(unit))
            domain_list.append(new_domain.getZonotope())
        return domain_list
    
    def getCoefLength(self):
        return len(self.alpha_i)
    
    def setValue(self, x):
        res = Zonotope()
        res.center = x
        res.alpha_i = list()
        return res
    
        # arithmetic
    def add(self, y):
        # print('in add', self.getInterval().left, self.getInterval().right)
        # print('self, c', self.center)
        # for i in self.alpha_i:
        #     print(i)

        # if isinstance(y, torch.Tensor):
        #     print('y', y)
        # else:
        #     print('y', y.getInterval().left, y.getInterval().right)
        # self + y
        res = Zonotope()
        if isinstance(y, torch.Tensor):
            res.center = self.center.add(y)
            res.alpha_i = [i.add(y) for i in self.alpha_i]
        else:
            res.center = self.center.add(y.center)
            l1 = self.getCoefLength()
            l2 = y.getCoefLength()
            res_l = res.getCoefLength()
            largest_l = max(l1, l2)
            shortest_l = min(l1, l2)
            for i in range(largest_l - res_l):
                res.alpha_i.append(var(0.0)) # take spaces

            for i in range(shortest_l):
                res.alpha_i[i] = self.alpha_i[i].add(y.alpha_i[i])
            if l1 < l2:
                for i in range(l1, l2):
                    res.alpha_i[i] = y.alpha_i[i]
            else:
                for i in range(l2, l1):
                    res.alpha_i[i] = self.alpha_i[i]
        # print('after add', res.getInterval().left, res.getInterval().right)
        if isinstance(y, torch.Tensor):
            res = self.getInterval().add(y).getZonotope()
        else:
            res = self.getInterval().add(y.getInterval()).getZonotope()
        return res

    def sub_l(self, y):
        # self - y
        res = Zonotope()
        if isinstance(y, torch.Tensor):
            res.center = self.center.sub(y)
            res.alpha_i = [i.sub(y) for i in self.alpha_i]
        else:
            res.center = self.center.sub(y.center)
            l1 = self.getCoefLength()
            l2 = y.getCoefLength()
            res_l = res.getCoefLength()
            largest_l = max(l1, l2)
            shortest_l = min(l1, l2)
            for i in range(largest_l - res_l):
                res.alpha_i.append(var(0.0)) # take spaces

            for i in range(shortest_l):
                res.alpha_i[i] = self.alpha_i[i].sub(y.alpha_i[i])
            if l1 < l2:
                for i in range(l1, l2):
                    res.alpha_i[i] = var(0.0).sub(y.alpha_i[i])
            else:
                for i in range(l2, l1):
                    res.alpha_i[i] = self.alpha_i[i]
        # print('after sub_l', res.getInterval().left, res.getInterval().right)

        if isinstance(y, torch.Tensor):
            res = self.getInterval().sub_l(y).getZonotope()
        else:
            res = self.getInterval().sub_l(y.getInterval()).getZonotope()
        return res

    def sub_r(self, y):
        # y - self

        res = Zonotope()
        if isinstance(y, torch.Tensor):
            res.center = y.sub(self.center)
            res.alpha_i = [y.sub(i) for i in self.alpha_i]
        else:
            res.center = y.center.sub(self.center)
            l1 = self.getCoefLength()
            l2 = y.getCoefLength()
            res_l = res.getCoefLength()
            largest_l = max(l1, l2)
            shortest_l = min(l1, l2)
            for i in range(largest_l - res_l):
                res.alpha_i.append(var(0.0)) # take spaces

            for i in range(shortest_l):
                res.alpha_i[i] = y.alpha_i[i].sub(self.alpha_i[i])
            if l1 < l2:
                for i in range(l1, l2):
                    res.alpha_i[i] = y.alpha_i[i]
            else:
                for i in range(l2, l1):
                    res.alpha_i[i] = var(0.0).sub(self.alpha_i[i])
        # print('after sub_r', res.getInterval().left, res.getInterval().right)
        if isinstance(y, torch.Tensor):
            res = self.getInterval().sub_r(y).getZonotope()
        else:
            res = self.getInterval().sub_r(y.getInterval()).getZonotope()
        return res

    def mul(self, y):
        # self * y
        # print('in mul', self.getInterval().left, self.getInterval().right)
        # print('self, c', self.center)
        # for i in self.alpha_i:
        #     print(i)
        # if isinstance(y, torch.Tensor):
        #     print('y', y)
        # else:
        #     print('y', y.getInterval().left, y.getInterval().right)

        res = Zonotope()
        if isinstance(y, torch.Tensor):
            res.center = self.center.mul(y)
            res.alpha_i = [i.mul(y) for i in self.alpha_i]

            res = self.getInterval().mul(y).getZonotope()
        else:
            # res.center = self.center.mul(y.center)
            # res.alpha_i = list()
            
            # l1 = self.getCoefLength()
            # l2 = y.getCoefLength()
            # max_l = max(l1, l2)
            # # equalize the length
            # for i in range(l1, max_l):
            #     self.alpha_i.append(var(0.0))
            # for i in range(l2, max_l):
            #     y.alpha_i.append(var(0.0))
            
            # for i in range(max_l):
            #     tmp_coef = self.center.mul(y.alpha_i[i]).add(y.center.mul(self.alpha_i[i]))
            #     res.alpha_i.append(tmp_coef)
            
            # # last noise coef: uv, u = sum abs(x_i), v = sum abs(y_i)
            # u = var(0.0)
            # v = var(0.0)
            # for i in range(l1):
            #     u = u.add(torch.abs(self.alpha_i[i]))
            # for i in range(l2):
            #     v = v.add(torch.abs(y.alpha_i[i]))
            res = self.getInterval().mul(y.getInterval()).getZonotope()
            # res.alpha_i.append(u.mul(v))
        # print('after mul', res.getInterval().left, res.getInterval().right)
        return res


    def div(self, y):

        # print('in div', self.getInterval().left, self.getInterval().right)
        # if isinstance(y, torch.Tensor):
        #     print('y', y)
        # else:
        #     print('y', y.getInterval().left, y.getInterval().right)
        # # y / self
        # # use mini-range approximation
        # res = Zonotope()
        # l1 = self.getCoefLength()
        # res_l = res.getCoefLength()
        # if res_l < l1:
        #     for i in range(res_l, l1):
        #         res.alpha_i.append(var(0.0))

        # tmp_interval = self.getInterval()
        # m = tmp_interval.left
        # n = tmp_interval.right

        # if m.data.item() <= 0 and n.data.item() >= 0:
        #     return Zonotope(N_INFINITY.data.item(), P_INFINITY.data.item())

        # t1 = torch.abs(m)
        # t2 = torch.abs(n)

        # a = torch.min(t1, t2)
        # b = torch.max(t1, t2)

        # alpha = var(-1.0).div(b.mul(b))
        # # i = ((1/a)-alpha*a, 2/b), alpha_0 = i.mid() 
        # dzeta = (((var(1.0)/a).sub(alpha.mul(a))).add(var(2.0).div(b))).div(2.0)
        # delta = var(2.0).div(b).sub(dzeta)

        # if tmp_interval.left.data.item() < 0.0:
        #     dzeta = dzeta.mul(var(-1.0))
        
        # res.center = alpha.mul(self.center).add(dzeta)
        # for i in range(l1):
        #     res.alpha_i[i] = alpha.mul(self.alpha_i[i])
        # res.alpha_i.append(delta)
        # # res = 1/self
        
        # res = res.mul(y)

        # print('after div', res.getInterval().left, res.getInterval().right)
        tmp_res = self.getInterval()
        tmp_res = tmp_res.div(var(1.0))
        res = tmp_res.getZonotope().mul(y)
        
        return res

    def exp(self):
        # e^(self)
        # print('in exp', self.getInterval().left, self.getInterval().right)
        # res = Zonotope()
        # l1 = self.getCoefLength()
        # res_l = res.getCoefLength()
        # if res_l < l1:
        #     for i in range(res_l, l1):
        #         res.alpha_i.append(var(0.0))
        
        # tmp_interval = self.getInterval()
        # a = tmp_interval.left
        # b = tmp_interval.right

        # ea = torch.exp(a)
        # eb = torch.exp(b)

        # alpha = (eb.sub(ea)).div(b.sub(a))
        # xs = torch.log(alpha)
        # maxdelta = alpha.mul(xs.sub(var(1.0).sub(a))).add(ea)
        # dzeta = alpha.mul(var(1.0).sub(xs))
        # # get the error
        # delta = maxdelta.div(var(2.0))

        # res.center = alpha.mul(self.center).add(dzeta)
        # for i in range(l1):
        #     res.alpha_i[i] = alpha.mul(self.alpha_i[i])
        # res.alpha_i.append(delta)

        # print('after exp', res.getInterval().left, res.getInterval().right)

        tmp_res = self.getInterval()
        res = tmp_res.exp().getZonotope()

        return res

    def sin(self):
        tmp_res = self.getInterval()
        res = tmp_res.sin().getZonotope()
        return res

    def cos(self):
        tmp_res = self.getInterval()
        res = tmp_res.cos().getZonotope()
        return res

    def max(self, y):
        res = Zonotope()
        res.alpha_i = list()

        tmp_interval = self.getInterval()
        a = tmp_interval.left
        b = tmp_interval.right

        if isinstance(y, torch.Tensor):
            if b.data.item() >= y.data.item():
                res.center = self.center
                for i in self.alpha_i:
                    res.alpha_i.append(self.alpha_i[i])
            else:
                return Zonotope(y.data.item(), y.data.item())
        else:
            l1 = self.getCoefLength()
            l2 = y.getCoefLength()
            for i in range(max(l1, l2)):
                res.alpha_i.append(var(0.0))
            
            tmp_interval_2 = y.getInterval()
            m = tmp_interval_2.left
            n = tmp_interval_2.right

            if b.data.item() >= n.data.item():
                res.center = self.center
                for i in range(l1):
                    res.alpha_i[i] = self.alpha_i[i]
            else:
                res.center = y.center
                for i in range(l2):
                    res.alpha_i[i] = y.alpha_i[i]
        
        # 
        tmp_res =(self.getInterval().max(y.getInterval())).getZonotope()
        return tmp_res

    def min(self, y):
        res = Zonotope()
        res.alpha_i = list()

        tmp_interval = self.getInterval()
        a = tmp_interval.left
        b = tmp_interval.right

        if isinstance(y, torch.Tensor):
            if b.data.item() <= y.data.item():
                res.center = self.center
                for i in self.alpha_i:
                    res.alpha_i.append(self.alpha_i[i])
            else:
                return Zonotope(y.data.item(), y.data.item())
        else:
            l1 = self.getCoefLength()
            l2 = y.getCoefLength()
            for i in range(max(l1, l2)):
                res.alpha_i.append(var(0.0))
            
            tmp_interval_2 = y.getInterval()
            m = tmp_interval_2.left
            n = tmp_interval_2.right

            if b.data.item() <= n.data.item():
                res.center = self.center
                for i in range(l1):
                    res.alpha_i[i] = self.alpha_i[i]
            else:
                res.center = y.center
                for i in range(l2):
                    res.alpha_i[i] = y.alpha_i[i]
        
        # return res
        tmp_res = (self.getInterval().min(y.getInterval())).getZonotope()
        return tmp_res




if __name__ == "__main__":
    a = Interval()
    b = Interval()
    print(a.add(b).left, a.add(b).right)
    # c = Interval().setValue(var(1.0))
    # print(c.left, c.right)