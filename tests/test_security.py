"""Verify the browser security policy on successful and error responses."""
from unittest import TestCase
from service import app


class TestSecurity(TestCase):
    """Security headers and cross-origin behavior."""

    def setUp(self):
        self.client = app.test_client()

    def test_security_headers(self):
        """It should set content, framing, CSP and referrer protections."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertTrue(response.headers["Referrer-Policy"])

    def test_hsts_on_https(self):
        """It should require HTTPS for later visits after a secure request."""
        response = self.client.get("/", base_url="https://localhost")
        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])

    def test_cors_request(self):
        """It should allow the public API origin without credential sharing."""
        response = self.client.get("/accounts", headers={"Origin": "https://client.example.com"})
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "https://client.example.com")
        self.assertNotIn("Access-Control-Allow-Credentials", response.headers)

    def test_cors_preflight(self):
        """It should permit JSON account updates through a CORS preflight."""
        response = self.client.options("/accounts/1", headers={
            "Origin": "https://client.example.com",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "Content-Type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("PUT", response.headers["Access-Control-Allow-Methods"])
        self.assertIn("Content-Type", response.headers["Access-Control-Allow-Headers"])

    def test_error_security_headers(self):
        """It should apply security policy to 404 responses too."""
        response = self.client.get("/missing-resource")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
