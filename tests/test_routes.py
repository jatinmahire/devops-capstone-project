"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from unittest.mock import patch
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


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
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
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
            response = self.client.post(BASE_URL, json=account.serialize())
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
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_list_accounts_empty(self):
        """It should return an empty list when no accounts exist"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_list_accounts(self):
        """It should list every persisted account"""
        accounts = self._create_accounts(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in response.get_json()}, {item.id for item in accounts})

    def test_read_account(self):
        """It should read the account identified by its ID"""
        account = self._create_accounts(1)[0]
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), account.serialize())

    def test_read_missing_account(self):
        """It should return 404 for an account that does not exist"""
        response = self.client.get(f"{BASE_URL}/999999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.get_json()["error"], "Not Found")

    def test_create_location(self):
        """It should return a Location that retrieves the created account"""
        response = self.client.post(BASE_URL, json=AccountFactory().serialize())
        location = response.headers["Location"]
        self.assertTrue(location.endswith(f"/accounts/{response.get_json()['id']}"))
        self.assertEqual(self.client.get(location).get_json(), response.get_json())

    def test_update_account(self):
        """It should persist all fields of an updated account"""
        account = self._create_accounts(1)[0]
        updated = account.serialize()
        updated.update(name="Updated Customer", email="updated@example.com", phone_number="555-0101")
        response = self.client.put(f"{BASE_URL}/{account.id}", json=updated)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), updated)
        self.assertEqual(self.client.get(f"{BASE_URL}/{account.id}").get_json(), updated)

    def test_update_missing_account(self):
        """It should reject updates to missing accounts"""
        response = self.client.put(f"{BASE_URL}/999999", json=AccountFactory().serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_invalid_media_type(self):
        """It should reject an update that is not JSON"""
        account = self._create_accounts(1)[0]
        response = self.client.put(f"{BASE_URL}/{account.id}", data="invalid", content_type="text/plain")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_missing_fields(self):
        """It should reject an incomplete account update"""
        account = self._create_accounts(1)[0]
        response = self.client.put(f"{BASE_URL}/{account.id}", json={"name": "Incomplete"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_account(self):
        """It should delete the account and make it unavailable"""
        account = self._create_accounts(1)[0]
        response = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")
        self.assertEqual(self.client.get(f"{BASE_URL}/{account.id}").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(BASE_URL).get_json(), [])

    def test_delete_missing_account(self):
        """It should make repeated DELETE requests idempotent"""
        self.assertEqual(self.client.delete(f"{BASE_URL}/999999").status_code, status.HTTP_204_NO_CONTENT)

    def test_create_invalid_date(self):
        """It should report an invalid date as a client validation error"""
        account = AccountFactory().serialize()
        account["date_joined"] = "invalid-date"
        self.assertEqual(self.client.post(BASE_URL, json=account).status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_without_content_type(self):
        """It should require the Content-Type header"""
        self.assertEqual(self.client.post(BASE_URL, data="{}").status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_unsupported_method(self):
        """It should return a JSON 405 response for unsupported methods"""
        response = self.client.patch(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.get_json()["status"], 405)

    def test_database_failure_returns_json(self):
        """It should return a structured 500 response after a database failure."""
        with patch.object(Account, "all", side_effect=RuntimeError("Database unavailable")):
            with patch.dict(app.config, {"PROPAGATE_EXCEPTIONS": False}):
                response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.get_json()["error"], "Internal Server Error")

    def test_create_without_optional_fields(self):
        """It should default the date and permit an omitted phone number."""
        payload = {"name": "New Customer", "email": "customer@example.com", "address": "123 Main Street"}
        response = self.client.post(BASE_URL, json=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.get_json()["phone_number"])
        self.assertTrue(response.get_json()["date_joined"])
