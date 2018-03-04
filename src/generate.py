#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from jinja2 import Template
import yaml
template = Template(open('template.inx.j2', 'r').read())
parameters = yaml.load(open('parameters.yml', 'r').read())
for machine in parameters['machines']:
    for language in parameters['languages']:
        for release in ['devel', 'production']:
            parameters['machine']  = machine
            parameters['language'] = language
            parameters['release']  = release
            if release == 'devel':
                open('../' + machine + '_dev_' + language + '.inx', 'w').write(template.render(parameters))
            else:
                open('../' + machine + '_' + language + '.inx', 'w').write(template.render(parameters))
