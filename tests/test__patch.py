import time
import unittest

import mongomock

try:
    import pymongo
    _HAVE_PYMONGO = True
except ImportError:
    _HAVE_PYMONGO = False

try:
    from unittest import mock
except ImportError:
    import mock

import platform
_USING_PYPY = platform.python_implementation() == 'PyPy'


@unittest.skipIf(not _HAVE_PYMONGO, 'pymongo not installed')
@unittest.skipIf(_USING_PYPY, 'PyPy does not handle mocking time sleep properly')
class PatchTest(unittest.TestCase):
    """Test the use of the patch function.

    Test functions in this test are embedded in inner function so that the
    patch decorator are only called at testing time.
    """

    @mongomock.patch()
    def test__decorator(self):
        client1 = pymongo.MongoClient()
        client1.db.coll.insert_one({'name': 'Pascal'})

        client2 = pymongo.MongoClient()
        self.assertEqual(['db'], client2.database_names())
        self.assertEqual('Pascal', client2.db.coll.find_one()['name'])
        client2.db.coll.drop()

        self.assertEqual(None, client1.db.coll.find_one())

    @mongomock.patch(on_new='create')
    def test__create_new(self):
        client1 = pymongo.MongoClient('myserver.example.com', port=12345)
        client1.db.coll.insert_one({'name': 'Pascal'})

        client2 = pymongo.MongoClient(host='myserver.example.com', port=12345)
        self.assertEqual('Pascal', client2.db.coll.find_one()['name'])

    @mongomock.patch()
    def test__error_new(self):
        # Valid because using the default server which was whitelisted by default.
        pymongo.MongoClient()

        with self.assertRaises(ValueError):
            pymongo.MongoClient('myserver.example.com', port=12345)

    @mongomock.patch((
        'mongodb://myserver.example.com:12345',
        'mongodb://otherserver.example.com:27017/default-db',
        'mongodb://[2001:67c:2e8:22::c100:68b]',
        'mongodb://[2001:67c:2e8:22::c100:68b]:1234',
        'mongodb://r1.example.net:27017,r2.example.net:27017/',
        '/var/lib/mongo.sock',
    ))
    def test__create_servers(self):
        pymongo.MongoClient('myserver.example.com', port=12345)
        pymongo.MongoClient('otherserver.example.com')
        pymongo.MongoClient('[2001:67c:2e8:22::c100:68b]')
        pymongo.MongoClient('mongodb://[2001:67c:2e8:22::c100:68b]:27017/base')
        pymongo.MongoClient('[2001:67c:2e8:22::c100:68b]', port=1234)
        pymongo.MongoClient('r1.example.net')
        pymongo.MongoClient('/var/lib/mongo.sock')

        with self.assertRaises(ValueError):
            pymongo.MongoClient()

    @mongomock.patch(on_new='timeout')
    @mock.patch(time.__name__ + '.sleep')
    def test__create_timeout(self, mock_sleep):
        pymongo.MongoClient()

        mock_sleep.reset_mock()

        with self.assertRaises(pymongo.errors.ServerSelectionTimeoutError):
            client = pymongo.MongoClient('myserver.example.com', port=12345)
            client.db.coll.insert_one({'name': 'Pascal'})

        mock_sleep.assert_called_once_with(30000)

    @mongomock.patch('example.com')
    def test__different_default_db(self):
        client_1 = pymongo.MongoClient('mongodb://example.com/db1')
        client_2 = pymongo.MongoClient('mongodb://example.com/db2')

        # Access the same data from different clients, despite the different DB.
        client_1.test_db.collection.insert_one({'name': 'Pascal'})
        self.assertEqual(['Pascal'], [d['name'] for d in client_2.test_db.collection.find()])

        # Access the data from "default DB" of client 1 but by its name from client 2.
        client_1.get_default_database().collection.insert_one({'name': 'Lascap'})
        self.assertEqual(['Lascap'], [d['name'] for d in client_2.db1.collection.find()])

        # Access the data from "default DB" of client 2 but by its name from client 1.
        client_2.get_default_database().collection.insert_one({'name': 'Caribou'})
        self.assertEqual(['Caribou'], [d['name'] for d in client_1.db2.collection.find()])


if __name__ == '__main__':
    unittest.main()
