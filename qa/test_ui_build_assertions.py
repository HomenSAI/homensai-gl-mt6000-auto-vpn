"""The dashboard patch pipeline must refuse missing or duplicated anchors."""
import ast
import copy
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDERS = ('build_sidebar_ui.py', 'simple_home_patch.py', 'hybrid_release_patch.py')
EXTRA_BUILDERS = {'visible_refresh_patch.py': {'replace', 'replace_fragment'},
                  'lazy_help_build.py': {'once'}}


def parsed(name):
    return ast.parse((ROOT / 'router' / name).read_text(encoding='utf8'))


def unchecked_fragment_replacements(tree, helpers):
    parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    failures=[]
    for node in ast.walk(tree):
        if not (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='replace'):
            continue
        base=node.func.value
        while isinstance(base,ast.Call) and isinstance(base.func,ast.Attribute) and base.func.attr=='replace':
            base=base.func.value
        # Constant template placeholders format newly written code; they do not patch existing source.
        if isinstance(base,ast.Constant) and isinstance(base.value,str):continue
        scope=parents.get(node)
        while scope is not None and not isinstance(scope,ast.FunctionDef):scope=parents.get(scope)
        receiver=node.func.value
        if (scope is None or scope.name not in helpers or not isinstance(receiver,ast.Name)
                or not any(isinstance(part,ast.Call) and isinstance(part.func,ast.Attribute)
                           and isinstance(part.func.value,ast.Name) and part.func.value.id==receiver.id
                           and part.func.attr=='count' for part in ast.walk(scope))):
            failures.append(node.lineno)
    return failures


class AssertedDashboardPatches(unittest.TestCase):
    def test_new_page_pipeline_source_and_fragments_use_count_checked_helpers(self):
        for name,helpers in EXTRA_BUILDERS.items():
            with self.subTest(builder=name):
                self.assertEqual(unchecked_fragment_replacements(parsed(name),helpers),[])

    def test_fragment_scan_catches_silent_patch_and_unchecked_helper(self):
        for text in ["def apply(source):\n ranking=source\n return ranking.replace('x','y')\n",
                     "def replace_fragment(fragment,old,new):\n return fragment.replace(old,new)\n"]:
            self.assertTrue(unchecked_fragment_replacements(ast.parse(text),{'replace_fragment'}))

    def test_visible_fragment_helper_refuses_missing_and_unexpected_multiplicity(self):
        helper=next(node for node in parsed('visible_refresh_patch.py').body
                    if isinstance(node,ast.FunctionDef) and node.name=='replace_fragment')
        namespace={}
        exec(compile(ast.Module(body=[helper],type_ignores=[]),'<visible fragment helper>','exec'),namespace)
        replace=namespace['replace_fragment']
        self.assertEqual(replace('before anchor after','anchor','new'),'before new after')
        self.assertEqual(replace('anchor anchor','anchor','new',expected=2),'new new')
        for value in ('missing','anchor anchor'):
            with self.assertRaisesRegex(ValueError,'VISIBLE-FRAGMENT-COUNT'):replace(value,'anchor','new')

    def test_source_replace_is_confined_to_count_checked_helpers(self):
        for name in BUILDERS:
            parents = {}
            tree = parsed(name)
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            calls = []
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'replace' and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == 'source'):
                    continue
                scope = parents.get(node)
                while scope is not None and not isinstance(scope, ast.FunctionDef):
                    scope = parents.get(scope)
                with self.subTest(builder=name, line=node.lineno):
                    self.assertIsNotNone(scope, 'unasserted dashboard source.replace')
                    self.assertEqual(scope.name, 'must_replace' if name == BUILDERS[0] else 'replace')
                    # The actual helper must inspect source.count(old), not merely `old in source`.
                    self.assertTrue(any(isinstance(part, ast.Call) and isinstance(part.func, ast.Attribute)
                                        and isinstance(part.func.value, ast.Name)
                                        and part.func.value.id == 'source' and part.func.attr == 'count'
                                        for part in ast.walk(scope)))
                calls.append(node)
            self.assertTrue(calls, name)

    def build_helper(self, value):
        helper = next(node for node in parsed(BUILDERS[0]).body
                      if isinstance(node, ast.FunctionDef) and node.name == 'must_replace')
        namespace = {'source': value}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), '<sidebar helper>', 'exec'), namespace)
        return namespace

    def test_single_anchor_is_replaced(self):
        namespace = self.build_helper('before anchor after')
        namespace['must_replace']('anchor', 'changed')
        self.assertEqual(namespace['source'], 'before changed after')

    def test_missing_or_duplicate_anchor_is_refused_without_change(self):
        for value in ('missing', 'anchor anchor'):
            with self.subTest(source=value):
                namespace = self.build_helper(value)
                with self.assertRaisesRegex(ValueError, 'Sidebar anchor count'):
                    namespace['must_replace']('anchor', 'changed')
                self.assertEqual(namespace['source'], value)

    def test_expected_multiple_occurrences_are_checked(self):
        namespace = self.build_helper('anchor anchor')
        namespace['must_replace']('anchor', 'changed', expected=2)
        self.assertEqual(namespace['source'], 'changed changed')
        with self.assertRaisesRegex(ValueError, 'Sidebar anchor count'):
            namespace['must_replace']('changed', 'new', expected=3)
        self.assertEqual(namespace['source'], 'changed changed')

    def test_explicit_first_of_multiple_occurrences_keeps_its_limit(self):
        namespace = self.build_helper('anchor anchor')
        namespace['must_replace']('anchor', 'changed', expected=2, limit=1)
        self.assertEqual(namespace['source'], 'changed anchor')

    def test_simple_and_hybrid_helpers_refuse_missing_or_duplicate_anchors(self):
        for name in BUILDERS[1:]:
            original = next(node for node in parsed(name).body
                            if isinstance(node, ast.FunctionDef) and node.name == 'apply')
            wrapper = copy.deepcopy(original)
            helper = next(node for node in wrapper.body
                          if isinstance(node, ast.FunctionDef) and node.name == 'replace')
            wrapper.body = [helper] + ast.parse('return replace, lambda: source').body
            namespace = {}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])),
                         '<%s helper>' % name, 'exec'), namespace)
            for value in ('missing', 'anchor anchor'):
                with self.subTest(builder=name, source=value):
                    replace, current = namespace['apply'](value)
                    with self.assertRaises((AssertionError, ValueError)):
                        replace('anchor', 'changed')
                    self.assertEqual(current(), value)
            replace, current = namespace['apply']('anchor')
            replace('anchor', 'changed')
            self.assertEqual(current(), 'changed')


if __name__ == '__main__':
    unittest.main()
