#!/usr/bin/env python

import json
from pprint import pprint
from typing import Any, Callable, Iterable, Optional


def get_selections(data: dict) -> list[dict]:
    ret = []
    forces = data['roster']['forces']
    for force in forces:
        ret.extend(force.get('selections', []))
    return ret


def get_categories(data: dict) -> list[dict]:
    ret = []
    forces = data['roster']['forces']
    for force in forces:
        ret.extend(force.get('categories', []))
    return ret


def primary_category(selection: dict) -> Optional[str]:
    for c in selection.get('categories', []):
        if c.get('primary', False):
            return c['name']


def group_by(xs: Iterable[Any], transform: Callable | str) -> dict:
    ret = {}
    for x in xs:
        if callable(transform):
            key = transform(x)
        elif isinstance(transform, str):
            key = x.get(transform)
        else:
            key = x
        if key not in ret:
            ret[key] = []
        ret[key].append(x)
    return ret


def uniq_by(xs: Iterable[Any], transform: Callable | str) -> list:
    groups = group_by(xs, transform)
    ret = []
    for k in sorted(groups.keys()):
        vals = groups.get(k)
        ret.append(vals[0])
    return ret


def get_rules(data: dict) -> list[dict]:
    rules = []
    for s in get_selections(data):
        rules.extend(s.get('rules', []))
    return uniq_by(rules, 'name')


def get_players(data: dict) -> list[dict]:
    selections = get_selections(data)
    groups = group_by(selections, primary_category)
    return groups.get('Player', [])


if __name__ == '__main__':
    import sys
    in_file = sys.argv[1]
    with open(in_file, 'r') as f:
        data = json.load(f)
    selections = get_selections(data)
    groups = group_by(selections, primary_category)
    pprint(get_rules(data))
    pprint(get_players(data))
