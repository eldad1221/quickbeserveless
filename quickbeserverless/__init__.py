import json
from quickbelog import Log
from cerberus import Validator
from inspect import getfullargspec

WEB_SERVER_ENDPOINTS = {}
WEB_SERVER_ENDPOINTS_VALIDATIONS = {}
WEB_SERVER_ENDPOINTS_DOCS = {}
WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES = {}


class EndPointValidator(Validator):

    def _validate_doc(self, constraint, field, value):
        """
        For documentation text
        :param constraint:
        :param field:
        :param value:
        :return:
        """
        pass

    def _validate_example(self, constraint, field, value):
        """
        For example value
        :param constraint:
        :param field:
        :param value:
        :return:
        """
        pass


def _endpoint_function(path: str):
    if path.startswith('/') and len(path) > 0:
        path = path[1:]
    if path in WEB_SERVER_ENDPOINTS:
        return WEB_SERVER_ENDPOINTS.get(path)
    else:
        raise NotImplementedError(f'No implementation for path /{path}.')


def get_endpoint_validator(path: str) -> Validator:
    if path in WEB_SERVER_ENDPOINTS_VALIDATIONS:
        return WEB_SERVER_ENDPOINTS_VALIDATIONS.get(path)
    else:
        return None


def is_valid_http_handler(func) -> bool:
    args_spec = getfullargspec(func=func)
    try:
        args_spec.annotations.pop('return')
    except KeyError:
        pass
    arg_types = args_spec.annotations.values()
    if len(arg_types) == 1 and issubclass(list(arg_types)[0], HttpSession):
        return True
    else:
        raise TypeError(
            f'Function {func.__qualname__} needs one argument, type {HttpSession.__qualname__}.Got spec: {args_spec}'
        )


class HttpSession:

    def __init__(self, body: dict = None, parameters: dict = None, headers: dict = None):
        self._response_status = 200
        self._response_headers = {}

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

    @property
    def response_headers(self) -> dict:
        return self._response_headers

    def get(self, name: str, default=None):
        return self._data.get(name, default)

    def set_status(self, status: int):
        self._response_status = status

    def set_response_header(self, key: str, value: str):
        self._response_headers[key] = value


def endpoint(path: str = None, validation: dict = None, doc: str = None, example=None):
    """
    Endpoint decorator
    :param path: Web path (route) to map
    :param validation: Validation schema, check this for more info https://docs.python-cerberus.org/en/stable/
    :param doc: Documentation text
    :param example: Example for function response
    :return:
    """

    def decorator(func):
        global WEB_SERVER_ENDPOINTS
        global WEB_SERVER_ENDPOINTS_VALIDATIONS
        global WEB_SERVER_ENDPOINTS_DOCS
        global WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES
        if path is None:
            web_path = str(func.__qualname__).lower().replace('.', '/').strip()
        else:
            web_path = path.strip()

        if web_path.startswith('/') and len(web_path) > 0:
            web_path = web_path[1:]

        if is_valid_http_handler(func=func):
            Log.debug(f'Registering endpoint: Path={web_path}, Function={func.__qualname__}')
            if web_path in WEB_SERVER_ENDPOINTS:
                raise FileExistsError(f'Endpoint {web_path} already exists.')

            WEB_SERVER_ENDPOINTS[web_path] = func

            if isinstance(validation, dict):
                validator = EndPointValidator(validation, purge_unknown=True)
                validator.allow_unknown = True
                WEB_SERVER_ENDPOINTS_VALIDATIONS[web_path] = validator

            if doc is not None:
                WEB_SERVER_ENDPOINTS_DOCS[web_path] = doc

            if example is not None:
                WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES[web_path] = example
            return func

    return decorator


def execute_endpoint(path: str, headers: dict, body: dict, parameters: dict) -> (dict, dict, int):

    session = HttpSession(
        body=body,
        parameters=parameters,
        headers=headers
    )
    return execute_endpoint_with_session(path=path, session=session)


def execute_endpoint_with_session(path: str, session: HttpSession) -> (dict, dict, int):
    validator = get_endpoint_validator(path=path)
    status_code = 200
    resp_body = {}

    if validator is not None:
        if not validator.validate(session.data):
            resp_body = validator.errors
            status_code = 400
        else:
            session._data = validator.normalized(session.data)

    if status_code == 200:
        resp_body = _endpoint_function(path=path)(session)
        status_code = session.response_status

    return resp_body, session.response_headers, status_code


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

    resp_body, response_headers, status_code = execute_endpoint(
        path=path, headers=event.get(EVENT_HEADERS_KEY, {}),
        body=body,
        parameters=event.get(EVENT_QUERY_STRING_KEY, {})
    )

    try:
        resp_body = json.dumps(resp_body)
    except ValueError:
        msg = 'Can not convert response body to JSON format.'
        Log.exception(msg)
        resp_body = msg
        status_code = 500

    return {

        "statusCode": status_code,
        EVENT_HEADERS_KEY: response_headers,
        EVENT_BODY_KEY: resp_body
    }
