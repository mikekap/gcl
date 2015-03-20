import unittest
from os import path

import gcl

def parse_ast(s, implicit_tuple=False):
  return gcl.reads(s, implicit_tuple=implicit_tuple)

def parse(s, env=None, implicit_tuple=False):
  return (gcl.reads(s, implicit_tuple=implicit_tuple)
             .eval(gcl.default_env.extend(env)))


def parse_tuple(s, env=None):
  return parse(s, env, implicit_tuple=True)


class TestBasics(unittest.TestCase):
  def testInteger(self):
    self.assertEquals(3, parse('3'))

  def testNegativeInteger(self):
    self.assertEquals(-3, parse('-3'))

  def testFloat(self):
    self.assertEquals(3.14, parse('3.14'))
    self.assertEquals(0.14, parse('.14'))

  def testSingleQuotedString(self):
    self.assertEquals("foo", parse("'foo'"))

  def testDoubleQuotedString(self):
    self.assertEquals("foo", parse('"foo"'))

  def testNull(self):
    self.assertEquals(None, parse('null'))

  def testBool(self):
    self.assertEquals(True, parse('true'))
    self.assertEquals(False, parse('false'))

  def testComments(self):
    self.assertEquals(3, parse("""
      # comment
      3
      """))

  def testComments(self):
    self.assertEquals(3, parse("""
      3
      # comment"""))

  def testImplicitTupleBasic(self):
    self.assertEquals([('foo', 3)], parse('foo=3;', implicit_tuple=True).items())

  def testImplicitTupleEmpty(self):
    self.assertEquals([], parse('', implicit_tuple=True).items())

  def testIdentifierWithDash(self):
    x = parse('hello-world', env={'hello-world': 1})
    self.assertEquals(1, x)

  def testIdentifierWithColon(self):
    x = parse('hello:world', env={'hello:world': 1})
    self.assertEquals(1, x)


class TestList(unittest.TestCase):
  def testEmptyList(self):
    self.assertEquals([], parse('[]'))

  def testSingletonList(self):
    self.assertEquals([1], parse('[1]'))

  def testTrailingComma(self):
    self.assertEquals([1], parse('[1, ]'))

  def testPair(self):
    self.assertEquals([1, 2], parse('[1, 2]'))

  def testNestedList(self):
    self.assertEquals([1, [2]], parse('[1, [2]]'))


class TestVariable(unittest.TestCase):
  def testVariableWithEnv(self):
    self.assertEquals('bar', parse('foo', env={'foo': 'bar'}))


class TestTuple(unittest.TestCase):
  def testEmptyTuple(self):
    self.assertEquals([], parse('{}').items())

  def testBoundIdentifiers(self):
    self.assertEquals([('foo', 'bar')], parse('{ foo = "bar" }').items())

  def testUnboundIdentifiers(self):
    t = parse('{ foo; }')
    try:
      print(t['foo'])
      self.fail('Should have thrown')
    except gcl.EvaluationError:
      pass  # Expected

  def testIndirectUnbound(self):
    t = parse('{ foo; bar = foo + 3; }')
    try:
      print(t['bar'])
      self.fail('Should have thrown')
    except gcl.EvaluationError:
      pass  # Expected

  def testVariableInSameScope(self):
    t = parse('{ foo = 3; bar = foo; }')
    self.assertEquals(3, t['bar'])

  def testVariableFromParentScope(self):
    t = parse('{ foo = global; bar = foo; }', { 'global': 3 })
    self.assertEquals(3, t['bar'])

  def testShadowGlobalScope(self):
    t = parse('{ foo = 3; bar = foo; }', { 'foo': 2 })
    self.assertEquals(3, t['bar'])

  def testDereferencing(self):
    t = parse("""{
      obj = {
        attr = 1;
      };
      one = obj.attr;
    }""");
    self.assertEquals(1, t['one'])

  def testDereferencingFromEnvironment(self):
    x = parse('obj.attr', env={ 'obj': { 'attr' : 1 }})
    self.assertEquals(1, x)


class TestApplication(unittest.TestCase):
  def setUp(self):
    self.env = {}
    self.env['inc'] = lambda x: x + 1
    self.env['foo'] = lambda: lambda: 3
    self.env['add'] = lambda x, y: x + y
    self.env['curry_add'] = lambda x: lambda y: x + y
    self.env['mk_obj'] = lambda x: { 'attr': x }

  def testFunctionApplication(self):
    self.assertEquals(3, parse('inc(2)', env=self.env))

  def testFunctionApplicationMultiArgs(self):
    self.assertEquals(5, parse('add(2, 3)', env=self.env))

  def testRepeatedFunctionCalls(self):
    self.assertEquals(3, parse('foo()()', env=self.env))

  def testNestedFunctionCalls(self):
    self.assertEquals(4, parse('inc(inc(2))', env=self.env))

  def testFunctionApplicationWithoutParens(self):
    self.assertEquals(3, parse('inc 2', env=self.env))

  def testChainedApplicationWithoutParens(self):
    self.assertEquals(5, parse('curry_add 2 3', env=self.env))

  def testTupleComposition(self):
    t = parse('{ foo = 1 } { bar = 2 }')
    self.assertEquals([
      ('bar', 2),
      ('foo', 1),
      ], sorted(t.items()))

  def testIndirectTupleComposition(self):
    t = parse("""
    {
      base = {
        name;
        hello = 'hello ' + name;
      };

      mine = base { name = 'Johnny' }
    }
    """)
    self.assertEquals('hello Johnny', t['mine']['hello'])

  def testIndirectTupleCompositionWithDefault(self):
    t = parse("""
    {
      base = {
        name = 'Barry';
        hello = 'hello ' + name;
      };

      mine = base { name = 'Johnny' }
    }
    """)
    self.assertEquals('hello Johnny', t['mine']['hello'])

  def testBaseDerefenceInRightTuple(self):
    # We also need this to EXTEND default tuples
    x = parse_tuple("""
    left = { a = 3 };
    right = left { a = base.a + 1 }
    """)
    self.assertEquals(4, x['right']['a'])

  def testDereferencingFromFunctionCall1(self):
    self.assertEquals(10, parse('mk_obj(10).attr', env=self.env))

  def testDereferencingFromFunctionCall2(self):
    self.assertEquals(10, parse('(mk_obj 10).attr', env=self.env))

  def testTupleApplicationAndDerefPrecedence(self):
    x = parse_tuple("""
    lib = {
      parent = { x = 1 }
    };

    composed = lib.parent { y = 2; }
    """)
    self.assertEquals(1, x['composed']['x'])
    self.assertEquals(2, x['composed']['y'])

  def testTripleApplication(self):
    t = parse("""
    { x = 1 } { y = 2 } { z = 3 }
    """)
    self.assertEquals(1, t['x'])
    self.assertEquals(2, t['y'])
    self.assertEquals(3, t['z'])

  def testApplyingTupleToString(self):
    # Applying the tuple to a string should index the tuple
    x = parse_tuple("""
    tuple = { x = 3 };
    y = tuple 'x';
    z = tuple('x')
    """)
    self.assertEquals(3, x['y'])
    self.assertEquals(3, x['z'])


  def testApplyingVariableToString(self):
    x = parse_tuple("""
    tuple = { x = 3 };
    var = 'x';
    y = tuple var;
    """)
    self.assertEquals(3, x['y'])

  def applyIntegerToList(self):
    x = parse_tuple("""
    list = [ 'a', 'b', 'c' ];
    y = list(0);
    z = list 1;
    """)
    self.assertEquals('a', x['y'])
    self.assertEquals('b', x['z'])


class TestExpressions(unittest.TestCase):
  def testAdd(self):
    self.assertEquals(5, parse('2 + 3'))

  def testAddStrings(self):
    self.assertEquals('foobar', parse('"foo" + "bar"'))

  def testMul(self):
    self.assertEquals(6, parse('2 * 3'))

  def testPrecedence(self):
    self.assertEqual(10, parse('2 * 3 + 4'))

  def testNot(self):
    self.assertEqual(False, parse('not true'))

  def testLogicalOpsAndPrecedence(self):
    self.assertEquals(True, parse('0 < 5 and 2 <= 2'))

  def testConditional(self):
    self.assertEquals(1, parse('if 0 < 5 then 1 else 2'))
    self.assertEquals(2, parse('if 5 < 0 then 1 else 2'))


class TestScoping(unittest.TestCase):
  def testOuterValueAvailableInInnerOne(self):
    t = parse_tuple("""
    x = 3;
    y = {
      z = x;
    };
    """)
    self.assertEquals(3, t['y']['z'])

  def testCompositedScopeNotAvailable(self):
    # Why is this? Well, it makes sense if there's also an x in the outer
    # scope. See next test.
    t = parse_tuple("""
    base = {
      x = 3;
    };
    y = base {
      z = x;
    }
    """)
    self.assertRaises(gcl.EvaluationError, lambda: t['y']['z'])

  def testVariableCantBeOverridenByContentsOfTuple(self):
    t = parse_tuple("""
    x = 1;
    base = {
      x = 2;
    };
    y = base {
      z = x;
    }
    """)
    # z should be 1, not 2 (even though we composite it with base, which also
    # has an x)
    # FIXME: To implement this: composition of tuples is not a single tuple,
    # but a construct that behaves like a tuple but has 2 lookups.
    self.assertEquals(1, t['y']['z'])

  def testCompositedScopeAvailableIfDeclared(self):
    t = parse_tuple("""
    base = {
      x = 3;
    };
    y = base {
      x;
      z = x;
    }
    """)
    self.assertEquals(3, t['y']['z'])

  def testCompositedValueInSubExpression(self):
    t = parse_tuple("""
    base = {
      x = 3;
    };
    y = base {
      x;  # <-- only if I put this here
      sub = {
        z = x;
      }
    }
    """)
    self.assertEquals(3, t['y']['sub']['z']);

  def testTwoLocalreferences(self):
    t = parse_tuple("""
    base = {
      x = 3;
      w = x
    };
    y = base {
      x = 4;
      z = x;
    }
    """)
    self.assertEquals(3, t['base']['w'])
    self.assertEquals(4, t['y']['z'])

  def testLocalValueOverridesOuterOne(self):
    t = parse_tuple("""
    x = 3;
    y = {
      x = 2;
      z = x;
    }
    """)
    self.assertEquals(2, t['y']['z'])

  def testLocalValueOverridesOuterOne_EvenIfUnbound(self):
    t = parse_tuple("""
    x = 3;
    y = {
      x;
      z = x;
    }
    """)
    try:
      t['y']['z']
      self.fail('Should have thrown')
    except gcl.EvaluationError as e:
      pass  # Expected

  def testRelativeImportWithDeclaration(self):
    t = parse("""
    {
      x = 1;
      y = x;
    }
    {
      y;
      x = 2;
      z = y;
    }
    """)
    # At this point, what should be the value of z?
    # To be locally analyzable, the value should be 1.
    # But to allow default values for 'declared tuples', which is
    # also desirable, the answer is the right declaration of 'x'
    # should override the left one, and the answer should be 2.

    self.assertEquals(2, t['z'])

  def testInheriting(self):
    # We need inheriting because we can't write
    #   z = { x = x }
    # (That would lead to infinite recursion)
    t = parse_tuple("""
    x = 1;
    y = 2;
    z = { inherit x y; w = 1 }
    """)
    self.assertEquals(1, t['z']['x'])
    self.assertEquals(2, t['z']['y'])

  def testInheritingAndCompositingLeft(self):
    x = parse_tuple("""
    parent = {
      foo = 1;
      child = {
        inherit foo;
      }
    };

    composed = parent { };
    """)
    self.assertEquals(1, x['composed']['child']['foo']);

  def testInheritingAndCompositingRight(self):
    x = parse_tuple("""
    parent = {
      foo;
      added = foo + 1;
    };

    foo = 1;

    composed = parent { inherit foo };
    """)
    self.assertEquals(1, x['composed']['foo']);

  def testDoubleInheriting(self):
    x = parse_tuple("""
    upper = {
      foo;
      sub = {
        inherit foo;
      }
    };
    final = upper { foo = 3; sub; lower = sub };
    """)
    self.assertEquals(3, x['final']['lower']['foo']);

  def testDoubleScopeAndInheriting(self):
    x = parse_tuple("""
      first = {};
      outer_thing = 'something';
      second = {
          copy = outer_thing;
      };
      foo = first second { }
    """)
    self.assertEquals('something', x['foo']['copy'])

  def testScopeGoodError(self):
    x = parse_tuple("""
    one = { foo = 3 };
    two = { };
    final = one two { };
    """)
    try:
      self.assertEquals(3, x['two']['moo'])
    except gcl.EvaluationError as e:
      self.assertTrue('Unknown' in str(e))

  def testDoubleApplicationAndResolutionGivesGoodError(self):
    x = parse_tuple("""
    one = { sub = { bar = foo }};
    two = { foo = boo };
    final = one two { sub; bla = sub.bar };
    """)
    try:
      self.assertEquals(3, x['final']['bla'])
    except gcl.EvaluationError as e:
      self.assertTrue('Unbound' in str(e))


class TestStandardLibrary(unittest.TestCase):
  def testPathJoin(self):
    self.assertEquals('a/b/c', parse("path_join('a', 'b', 'c')"))


class TestIncludes(unittest.TestCase):
  def parse(self, fname, s):
    return gcl.loads(s, filename=fname, loader=self.loader)

  def loader(self, base, rel):
    target_path = gcl.find_relative(path.dirname(base), rel)
    return gcl.loads('loaded_from = %r' % target_path)

  def testRelativeInclude(self):
    t = self.parse('/home/me/file', 'inc = include "other_file"')
    self.assertEquals('/home/me/other_file', t['inc']['loaded_from'])

  def testRelativeIncludeUp(self):
    t = self.parse('/home/me/file', 'inc = include "../other_file"')
    self.assertEquals('/home/other_file', t['inc']['loaded_from'])

  def testAbsoluteInclude(self):
    t = self.parse('/home/me/file', 'inc = include "/other_file"')
    self.assertEquals('/other_file', t['inc']['loaded_from'])

  def testIncludeWithApplyPrecedence(self):
    x = self.parse('/home/me/file', 'inc = include "other_file.gcl" { foo = 3 };')
    self.assertEquals(3, x['inc']['foo']);
