import json
import unittest
from quickbelog import Log
from quickbeserverless import execute_endpoint, aws_lambda_handler, endpoint, HttpSession

GREETING = 'Hello'
NAME = 'Suzi'
PATH = 'hello'
EXPECTED_RESULT = f'{GREETING} {NAME}'
TEST_BODY = {
        'name': NAME
    }
TEST_EVENT = {
    'path': PATH,
    'body': TEST_BODY
}


@endpoint(validation={
    'name': {'required': True, 'type': 'string'}
}
)
def hello(session: HttpSession):
    session.set_response_header('h1', '123')
    name = session.get('name')
    if name.upper() in ['ERROR']:
        session.set_response_header('h1', name)
        session.set_status(500)
    return f"{GREETING} {name}"


class AsLambdaEventTestCase(unittest.TestCase):

    def test_endpoint_missing_field(self):
        body, resp_headers, status = execute_endpoint(headers={}, body={}, parameters={}, path=PATH)
        self.assertEqual(400, status)
        self.assertIn('name', body)

    def test_endpoint_error_500(self):
        name = 'error'
        body, resp_headers, status = execute_endpoint(headers={}, body={}, parameters={'name': name}, path=PATH)
        self.assertEqual({'h1': name}, resp_headers)
        self.assertEqual(500, status)

    def test_endpoint(self):
        body, resp_headers, status = execute_endpoint(headers={}, body=TEST_BODY, parameters={}, path=PATH)
        self.assertEqual({'h1': '123'}, resp_headers)
        self.assertEqual(200, status)
        self.assertEqual(EXPECTED_RESULT, body)

    def test_as_aws_lambda(self):
        result = aws_lambda_handler(event=TEST_EVENT)
        Log.debug(f'Got result: {result}')
        self.assertIsNotNone(result)
        self.assertEqual(json.dumps(EXPECTED_RESULT), result.get('body'))


if __name__ == '__main__':
    unittest.main()
