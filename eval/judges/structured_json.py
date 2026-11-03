"""Small JSON Schema constructors for frame-grounded review responses."""

def obj(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def array(items, **limits):
    return {'type': 'array', 'items': items, **limits}


def response_format(name, properties):
    return {'type': 'json_schema', 'json_schema': {
        'name': name, 'strict': True, 'schema': obj(properties)}}


STRING = {'type': 'string'}
BOOLEAN = {'type': 'boolean'}


def frame_indices(count):
    return array({'type': 'integer', 'minimum': 1, 'maximum': count})
