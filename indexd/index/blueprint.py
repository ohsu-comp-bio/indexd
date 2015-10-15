import re
import flask
import jsonschema

from indexd.errors import UserError
from indexd.errors import PermissionError

from .schema import PUT_RECORD_SCHEMA
from .schema import POST_RECORD_SCHEMA

from .errors import NoRecordFound
from .errors import MultipleRecordsFound
from .errors import RevisionMismatch


blueprint = flask.Blueprint('index', __name__)

blueprint.config = dict()
blueprint.index_driver = None

@blueprint.route('/index/', methods=['GET'])
def get_index():
    '''
    Returns a list of records.
    '''
    limit = flask.request.args.get('limit')
    try: limit = 100 if limit is None else int(limit)
    except ValueError as err:
        raise UserError('limit must be an integer')

    if limit <= 0 or limit > 1024:
        raise UserError('limit must be between 1 and 1024')

    size = flask.request.args.get('size')
    try: size = size if size is None else int(size)
    except ValueError as err:
        raise UserError('size must be an integer')

    if size is not None and size < 0:
        raise UserError('size must be > 0')

    start = flask.request.args.get('start', '')

    hashes = flask.request.args.getlist('hash')
    hashes = [tuple(h.split(':', 1)) for h in hashes]

    if limit < 0 or limit > 1024:
        raise UserError('limit must be between 0 and 1024')

    ids = blueprint.index_driver.ids(
#        hashes=hashes,
#        size=size,
        start=start,
        limit=limit,
    )

    base = {
        'ids': ids,
        'limit': limit,
        'start': start,
        'hashes': hashes,
    }

    return flask.jsonify(base), 200

@blueprint.route('/index/<record>', methods=['GET'])
def get_index_record(record):
    '''
    Returns a record.
    '''
    ret = blueprint.index_driver.get(record)

    return flask.jsonify(ret), 200

@blueprint.route('/index/', methods=['POST'])
def post_index_record():
    '''
    Create a new record.
    '''
    try: jsonschema.validate(flask.request.json, POST_RECORD_SCHEMA)
    except jsonschema.ValidationError as err:
        raise UserError(err)

    form = flask.request.json['form']
    size = flask.request.json['size']
    urls = flask.request.json['urls']
    hashes = flask.request.json['hashes']

    did, rev = blueprint.index_driver.add(form, size,
        urls=urls,
        hashes=hashes,
    )

    ret = {
        'did': did,
        'rev': rev,
    }

    return flask.jsonify(ret), 200

@blueprint.route('/index/<record>', methods=['PUT'])
def put_index_record(record):
    '''
    Update an existing record.
    '''
    rev = flask.request.args.get('rev')
    if rev is None:
        raise UserError('no revision specified')

    try: jsonschema.validate(flask.request.json, PUT_RECORD_SCHEMA)
    except jsonschema.ValidationError as err:
        raise UserError(err)

    size = flask.request.json['size']
    urls = flask.request.json['urls']
    hashes = flask.request.json['hashes']

    did, rev = blueprint.index_driver.update(record, rev,
        size=size,
        urls=urls,
        hashes=hashes,
    )

    ret = {
        'did': record,
        'rev': rev,
    }

    return flask.jsonify(ret), 200

@blueprint.route('/index/<record>', methods=['DELETE'])
def delete_index_record(record):
    '''
    Delete an existing sign.
    '''
    rev = flask.request.args.get('rev')
    if rev is None:
        raise UserError('no revision specified')

    blueprint.index_driver.delete(record, rev)

    return '', 200

@blueprint.errorhandler(NoRecordFound)
def handle_no_record_error(err):
    return flask.jsonify(error=str(err)), 404

@blueprint.errorhandler(MultipleRecordsFound)
def handle_multiple_records_error(err):
    return flask.jsonify(error=str(err)), 409

@blueprint.errorhandler(UserError)
def handle_user_error(err):
    return flask.jsonify(error=str(err)), 400

@blueprint.errorhandler(PermissionError)
def handle_permission_error(err):
    return flask.jsonify(error=str(err)), 403

@blueprint.errorhandler(RevisionMismatch)
def handle_revision_mismatch(err):
    return flask.jsonify(error=str(err)), 409

@blueprint.record
def get_config(setup_state):
    config = setup_state.app.config['INDEX']
    blueprint.index_driver = config['driver']
