import unittest
from quickbeserverless import HttpSession, _is_valid_http_handler


def demo_1(session: HttpSession):
    return session.get('text')


def demo_2(session: HttpSession, s: str):
    return session.get('text')


def demo_3(session: str):
    return 'text'


class WebServerTestCase(unittest.TestCase):

    def test_http_handler(self):

        self.assertEqual(True, _is_valid_http_handler(func=demo_1))

        with self.assertRaises(TypeError):
            self.assertEqual(True, _is_valid_http_handler(func=demo_2))

        with self.assertRaises(TypeError):
            self.assertEqual(True, _is_valid_http_handler(func=demo_3))


if __name__ == '__main__':
    unittest.main()
