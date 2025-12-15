#!/usr/bin/env python

from dataclasses import dataclass
import json
from pprint import pprint
from typing import Any, Callable, Iterable, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt


COLUMN_ORDER = [
    'Player',
    'MA', 
    'ST', 
    'AG', 
    'AV',  
    'Skills & Traits', 
    'Primary', 
    'Secondary', 
    'Cost', 
    'SPP', 
    'Keywords'
]


def render(**context) -> str:
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape()
    )
    md = MarkdownIt()
    env.filters['md'] = md.render
    template = env.get_template('bb_cards.html.j2')
    return template.render(COLUMN_ORDER=COLUMN_ORDER, **context)


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


def dedupe_by(xs: Iterable[Any], transform: Callable | str) -> list:
    groups = group_by(xs, transform)
    ret = []
    for k in sorted(groups.keys()):
        vals = groups.get(k)
        count = len(vals)
        entry = vals[0]
        entry['count'] = count
        ret.append(entry)
    return ret


def characteristics_dict(characteristics: list[dict]) -> dict:
    return { c['name']: c['$text'] for c in characteristics }


def cost_dict(costs: list[dict]) -> dict:
    return { c['name']: c['value'] for c in costs }


@dataclass
class Profile:
    id: str
    name: str
    characteristics: dict

    @staticmethod
    def parse(data: dict):
        chars = characteristics_dict(data.get('characteristics', []))
        return Profile(
            id=data['id'],
            name=data['name'],
            characteristics=chars
        )


def get_profiles(data: dict) -> list[Profile]:
    all_profiles = []
    for s in get_selections(data):
        all_profiles.extend(s.get('profiles', []))
    
    profiles = dedupe_by(all_profiles, 'id')
    profiles = [Profile.parse(p) for p in profiles]
    profiles.sort(key=lambda x: x.name)
    return profiles


def merge_costs(costs_list: list[dict]) -> dict:
    merged = {}
    for costs in costs_list:
        for name, value in costs.items():
            if name in merged:
                merged[name] += value
            else:
                merged[name] = value
    return merged


@dataclass
class Player:
    name: str
    profiles: list[Profile]
    costs: dict
    primary_category: Optional[str]
    category_names: list[str]
    custom_name: Optional[str]
    selections: list[dict]
    rules: list[dict]
    characteristics: dict

    @staticmethod
    def parse(data: dict):
        profiles = [Profile.parse(p) for p in data.get('profiles', [])]
        primary_profile = profiles[0] if profiles else None
        costs = cost_dict(data.get('costs', []))
        primary_cat = primary_category(data)
        categories = data.get('categories', [])
        category_names = [c['name'] for c in categories]
        selections = data.get('selections', [])
        all_costs = [costs]
        all_rules = []
        all_rules.extend(data.get('rules', []))
        for s in selections:
            if 'costs' in s:
                all_costs.append(cost_dict(s['costs']))
            all_rules.extend(s.get('rules', []))
        total_costs = merge_costs(all_costs)
        all_rules = uniq_by(all_rules, 'name')
        characteristics = primary_profile.characteristics if primary_profile else {}
        if 'TV' in total_costs:
            # Add commas to number
            characteristics['Cost'] = f"{total_costs['TV']:,}"
        if 'SPP' in total_costs:
            characteristics['SPP'] = str(total_costs['SPP'])
        characteristics['Player'] = data['name']
        return Player(
            name=data['name'],
            profiles=profiles,
            costs=total_costs,
            primary_category=primary_cat,
            category_names=category_names,
            custom_name=data.get('customName'),
            selections=selections,
            rules=all_rules,
            characteristics=characteristics
        )


def get_rules(data: dict) -> list[dict]:
    rules = []
    for s in get_selections(data):
        rules.extend(s.get('rules', []))
    return uniq_by(rules, 'name')


def get_players(data: dict) -> list[Player]:
    selections = get_selections(data)
    groups = group_by(selections, primary_category)
    players_data = groups.get('Player', [])
    players = [Player.parse(p) for p in players_data]
    return players


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
            special_rules = []
            for sr in o['selections']:
                special_rules.extend(sr.get('rules', []))
            special_rules.sort(key=lambda x: x['name'])
        else:
            other_options.append(o)
    other_options.sort(key=lambda x: x['name'])
    return league, special_rules, other_options


def render_team(data: dict, include_css=True) -> str:
    rules = get_rules(data)
    players = get_players(data)
    profiles = get_profiles(data)
    name = data['roster']['name']
    tv = data['roster']['costs'][0]['value']
    league, special_rules, options = team_management_options(data)
    return render(name=name, 
                  tv=tv,
                  league=league,  
                  special_rules=special_rules,
                  rules=rules, 
                  players=players, 
                  profiles=profiles,
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
