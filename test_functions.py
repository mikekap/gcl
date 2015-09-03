import unittest
from os import path

import gcl


class TestStringInterpolation(unittest.TestCase):
  def testStringInterpolation(self):
    x = gcl.loads("""
    things = { foo = 'FOO'; bar = 'BAR' };
    y = fmt('Hey {foo}, are you calling me a {bar}?', things)
    """)
    self.assertEquals('Hey FOO, are you calling me a BAR?', x['y'])

  def testLazyStringInterpolation(self):
    x = gcl.loads("""
    things = { foo = 'FOO'; boom; };
    y = fmt('Hi {foo}', things)
    """)
    self.assertEquals('Hi FOO', x['y'])

  def testSubInterpolation(self):
    x = gcl.loads("""
    things = { sub = { foo = 'FOO'; boom } };
    y = fmt('Hi {sub.foo}', things)
    """)
    self.assertEquals('Hi FOO', x['y'])

  def testImplicitScope(self):
    x = gcl.loads("""
    things = { foo = 'FOO'; boom };
    y = fmt 'Hi {things.foo}'
    """)
    self.assertEquals('Hi FOO', x['y'])

  def testMap(self):
    x = gcl.loads("""
    lst = [1, 2];
    y = map(lambda x: {hello = x}, lst)
    """)
    self.assertEquals(1, x['y'][0]['hello'])
    self.assertEquals(2, x['y'][1]['hello'])

  def testFilter(self):
    x = gcl.loads("""
    lst = [1, 2, 3];
    y = filter(lambda x: x % 2 == 0, lst)
    """)
    self.assertEquals([2], x['y'])
