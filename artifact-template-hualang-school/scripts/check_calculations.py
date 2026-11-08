#!/usr/bin/env python3
"""deck-spec calculations 的安全四则运算与比较语义校验。"""
from __future__ import annotations

import ast
import math

FIELDS = ('comparison_id', 'subject', 'baseline', 'perspective', 'period', 'unit',
          'formula', 'inputs', 'expected', 'tolerance')
SEMANTIC_FIELDS = ('subject', 'baseline', 'perspective', 'period', 'unit')


def _number(value, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{path} 必须是有限数值，不能为 NaN、无穷、布尔值或字符串。')
    return float(value)


def _evaluate(node, inputs, path):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, inputs, path)
    if isinstance(node, ast.Constant):
        return _number(node.value, path)
    if isinstance(node, ast.Name):
        if node.id not in inputs:
            raise ValueError(f'{path} 引用了 inputs 中不存在的变量 {node.id}。')
        return inputs[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate(node.operand, inputs, path)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left = _evaluate(node.left, inputs, path)
        right = _evaluate(node.right, inputs, path)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ValueError(f'{path} 出现除零，请检查 inputs 与公式。')
        return left / right
    raise ValueError(f'{path} 仅允许 inputs 变量、有限数字、括号和 + - * /；'
                     '禁止函数、属性、乘方及任意 eval。')


def check_calculations(calculations):
    """返回复算报告；结构、语义及 expected 差异始终抛错，不能通过宽松质量模式绕过。"""
    if calculations is None:
        calculations = []
    if isinstance(calculations, dict):
        calculations = calculations.get('calculations', [])
    if not isinstance(calculations, list):
        raise ValueError('calculations 必须是数组；每项包含完整的比较语义与复算字段。')
    records = []
    identities = {}
    for index, item in enumerate(calculations):
        path = f'calculations[{index}]'
        if not isinstance(item, dict):
            raise ValueError(f'{path} 必须是对象。')
        for field in FIELDS:
            if field not in item:
                raise ValueError(f'{path}.{field} 缺失；请补齐比较对象、基线、视角、期间和单位。')
        for field in ('comparison_id', 'subject', 'baseline', 'perspective', 'period', 'unit', 'formula'):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f'{path}.{field} 必须是非空字符串，避免数值正确但比较语义缺失。')
        comparison_id = item['comparison_id'].strip()
        identity = tuple(item[field].strip() for field in SEMANTIC_FIELDS)
        if comparison_id in identities and identities[comparison_id] != identity:
            previous = identities[comparison_id]
            changed = [field for field, old, new in zip(SEMANTIC_FIELDS, previous, identity) if old != new]
            raise ValueError(f'{path} 与既有 comparison_id={comparison_id} 的 '
                             f'{"、".join(changed)} 不一致；跨页主体、基线、视角、期间或单位不一致。')
        identities[comparison_id] = identity
        if not isinstance(item['inputs'], dict):
            raise ValueError(f'{path}.inputs 必须是变量名到有限数值的对象。')
        inputs = {}
        for name, value in item['inputs'].items():
            if not isinstance(name, str) or not name.isidentifier():
                raise ValueError(f'{path}.inputs 的变量名 {name!r} 不是合法标识符。')
            inputs[name] = _number(value, f'{path}.inputs.{name}')
        expected = _number(item['expected'], f'{path}.expected')
        tolerance = _number(item['tolerance'], f'{path}.tolerance')
        if tolerance < 0:
            raise ValueError(f'{path}.tolerance 不能为负数。')
        try:
            tree = ast.parse(item['formula'], mode='eval')
        except SyntaxError as exc:
            raise ValueError(f'{path}.formula 不是合法四则运算表达式：{exc.msg}。') from exc
        if len(list(ast.walk(tree))) > 80:
            raise ValueError(f'{path}.formula 过于复杂；请拆成多项可审计计算。')
        actual = _evaluate(tree, inputs, f'{path}.formula')
        if not math.isfinite(actual):
            raise ValueError(f'{path}.formula 的计算结果不是有限数值。')
        difference = actual - expected
        passed = math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance + 1e-9)
        record = dict(item)
        record.update({
            'comparison_id': comparison_id,
            'actual': actual,
            'expected': expected,
            'difference': difference,
            'effective_tolerance': tolerance + 1e-9,
            'passed': passed,
            'error': None if passed else (
                f'复算值 {actual:.12g} 与 expected {expected:.12g} 不符，'
                f'差额 {difference:.12g}，容差 {tolerance:g}；'
                '请核对公式、inputs、主体、基线、视角、期间与单位。'),
        })
        if not passed:
            raise ValueError(f'{path} 复算不一致：{record["error"]}')
        records.append(record)
    return {'count': len(records), 'passed': True, 'results': records}
