import json
from quickbelog import Log
from cerberus import Validator
from inspect import getfullargspec

WEB_SERVER_ENDPOINTS = {}
WEB_SERVER_ENDPOINTS_VALIDATIONS = {}


def _endpoint_function(path: str):
    if path.startswith('/') and len(path) > 0:
        path = path[1:]
    if path in WEB_SERVER_ENDPOINTS:
        return WEB_SERVER_ENDPOINTS.get(path)
    else:
        raise NotImplementedError(f'No implementation for path /{path}.')


def _endpoint_validator(path: str) -> Validator:
    if path in WEB_SERVER_ENDPOINTS_VALIDATIONS:
        return WEB_SERVER_ENDPOINTS_VALIDATIONS.get(path)
    else:
        return None


def _is_valid_http_handler(func) -> bool:
    args_spec = getfullargspec(func=func)
    try:
        args_spec.annotations.pop('return')
    except KeyError:
        pass
    arg_types = args_spec.annotations.values()
    if len(arg_types) == 1 and HttpSession in arg_types:
        return True
    else:
        raise TypeError(
            f'Function {func.__qualname__} needs one argument, type {HttpSession.__qualname__}.Got spec: {args_spec}'
        )


class HttpSession:

    def __init__(self, body: dict = None, parameters: dict = None, headers: dict = None):
        self._response_status = 200

        if body is None:
            body = {}
        self._data = body

        self._headers = headers

        if parameters is not None and isinstance(parameters, dict):
            self._data.update(parameters)

    @property
    def request_headers(self) -> dict:
        return self._headers

    @property
    def data(self) -> dict:
        return self._data

    @property
    def response_status(self) -> int:
        return self._response_status

    def get(self, name: str, default=None):
        return self._data.get(name, default)

    def set_status(self, status: int):
        self._response_status = status


def endpoint(path: str = None, validation: dict = None):

    def decorator(func):
        global WEB_SERVER_ENDPOINTS
        global WEB_SERVER_ENDPOINTS_VALIDATIONS
        if path is None:
            web_path = str(func.__qualname__).lower().replace('.', '/').strip()
        else:
            web_path = path.strip()

        if web_path.startswith('/') and len(web_path) > 0:
            web_path = web_path[1:]

        if _is_valid_http_handler(func=func):
            Log.debug(f'Registering endpoint: Path={web_path}, Function={func.__qualname__}')
            if web_path in WEB_SERVER_ENDPOINTS:
                raise FileExistsError(f'Endpoint {web_path} already exists.')
            WEB_SERVER_ENDPOINTS[web_path] = func
            if isinstance(validation, dict):
                validator = Validator(validation)
                validator.allow_unknown = True
                WEB_SERVER_ENDPOINTS_VALIDATIONS[web_path] = validator
            return func

    return decorator


EVENT_BODY_KEY = 'body'
EVENT_HEADERS_KEY = 'headers'
EVENT_QUERY_STRING_KEY = 'queryStringParameters'


def aws_lambda_handler(event: dict, context=None):

    path = event.get('path', '/error')

    if context is not None:
        Log.debug(f'Lambda function: {context.function_name}, path: {path}.')

    body = event.get(EVENT_BODY_KEY, '{}')
    try:
        if body is None:
            body = {}
        elif isinstance(body, dict):
            pass
        elif isinstance(body, str):
            body = json.loads(body)
    except (ValueError, TypeError):
        pass

    session = HttpSession(
        body=body,
        parameters=event.get(EVENT_QUERY_STRING_KEY, {}),
        headers=event.get(EVENT_HEADERS_KEY)
    )
    validator = _endpoint_validator(path=path)
    status_code = 200
    resp_body = {}

    try:
        if validator is not None:
            if not validator.validate(session.data):
                resp_body = validator.errors
                status_code = 400
                raise ValueError()

        resp_body = _endpoint_function(path=path)(session)
    except ValueError:
        pass

    try:
        resp_body = json.dumps(resp_body)
    except ValueError:
        msg = 'Can not convert response body to JSON format.'
        Log.exception(msg)
        resp_body = msg
        status_code = 500

    return {
        "statusCode": status_code,
        "body": resp_body
    }
