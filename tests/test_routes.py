"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""

import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {"wsgi.url_scheme": "https"}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        talisman.force_https = False
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################
    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []

        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(
                BASE_URL,
                json=account.serialize(),
                content_type="application/json",
                environ_overrides=HTTPS_ENVIRON,
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )

            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)

        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################
    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get(
            "/",
            environ_overrides=HTTPS_ENVIRON,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get(
            "/",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'; object-src 'none'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)

    def test_cors_security(self):
        """It should return a CORS header"""
        response = self.client.get(
            "/",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check for the CORS header
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "*",
        )

    def test_health(self):
        """It should be healthy"""
        response = self.client.get(
            "/health",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()

        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(
            BASE_URL,
            json={"name": "not enough data"},
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()

        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]

        response = self.client.get(
            f"{BASE_URL}/{account.id}",
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["address"], account.address)
        self.assertEqual(data["phone_number"], account.phone_number)
        self.assertEqual(data["date_joined"], str(account.date_joined))

    def test_get_account_not_found(self):
        """It should not Read an Account that does not exist"""
        response = self.client.get(
            f"{BASE_URL}/0",
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_account_list(self):
        """It should Get a list of Accounts"""
        self._create_accounts(5)

        response = self.client.get(
            BASE_URL,
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_get_empty_account_list(self):
        """It should Get an empty list if no Accounts exist"""
        response = self.client.get(
            BASE_URL,
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(data, [])

    def test_update_account(self):
        """It should Update an existing Account"""
        account = self._create_accounts(1)[0]

        account_data = account.serialize()
        account_data["name"] = "Updated Name"

        response = self.client.put(
            f"{BASE_URL}/{account.id}",
            json=account_data,
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(data["name"], "Updated Name")
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["address"], account.address)
        self.assertEqual(data["phone_number"], account.phone_number)

    def test_update_account_not_found(self):
        """It should not Update an Account that does not exist"""
        account = AccountFactory()
        account_data = account.serialize()

        response = self.client.put(
            f"{BASE_URL}/0",
            json=account_data,
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account(self):
        """It should Delete an Account"""
        account = self._create_accounts(1)[0]

        response = self.client.delete(
            f"{BASE_URL}/{account.id}",
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(
            f"{BASE_URL}/{account.id}",
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account_not_found(self):
        """It should Delete an Account even if it does not exist"""
        response = self.client.delete(
            f"{BASE_URL}/0",
            content_type="application/json",
            environ_overrides=HTTPS_ENVIRON,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)