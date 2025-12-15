#!/usr/bin/env python

import json
from pprint import pprint
from typing import Any, Callable, Iterable, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render(**context) -> str:
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape()
    )
    template = env.get_template('bb_cards.html.j2')
    return template.render(**context)


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


def team_management_options(data: dict):
    selections = get_selections(data)
    groups = group_by(selections, primary_category)
    options = groups.get('Team Management', [])
    other_options = []
    league = None
    special_rules = None
    for o in options:
        if o['name'] == 'Team League':
            league = o['selections'][0]['name']
        elif o['name'] == 'Special Rules':
            special_rules = o
        else:
            other_options.append(o)
    other_options.sort(key=lambda x: x['name'])
    return league, special_rules, other_options


def render_team(data: dict, include_css=True) -> str:
    rules = get_rules(data)
    players = get_players(data)
    name = data['roster']['name']
    tv = data['roster']['costs'][0]['value']
    league, special_rules, options = team_management_options(data)
    return render(name=name, 
                  tv=tv,
                  league=league,  
                  special_rules=special_rules,
                  rules=rules, 
                  players=players, 
                  team_management_options=options, 
                  include_css=include_css)


if __name__ == '__main__':
    import sys
    in_file = sys.argv[1]
    with open(in_file, 'r') as f:
        data = json.load(f)
    selections = get_selections(data)
    groups = group_by(selections, primary_category)
    print(render_team(data, include_css=False))
    with open('out.html', 'w') as f:
        f.write(render_team(data))
