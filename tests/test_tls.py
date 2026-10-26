"""Exercise the actual API functions against local TLS, without GPIO or PiKVM."""

import ast
import contextlib
import http.server
import io
import json
import os
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from requests.auth import HTTPBasicAuth


class TLSRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        openssl = shutil.which("openssl")
        if not openssl:
            raise unittest.SkipTest("OpenSSL is required for the local TLS fixture")
        cls.temporary = tempfile.TemporaryDirectory(prefix="keybow-tls-")
        cls.addClassCleanup(cls.temporary.cleanup)
        root = Path(cls.temporary.name)
        cls.certificate = root / "server.pem"
        key = root / "server.key"
        subprocess.run(
            [
                openssl,
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(key),
                "-out",
                str(cls.certificate),
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-config",
                os.devnull,
                "-addext",
                "subjectAltName=DNS:localhost",
                "-addext",
                "basicConstraints=critical,CA:TRUE",
                "-addext",
                "keyUsage=critical,digitalSignature,keyCertSign",
                "-addext",
                "extendedKeyUsage=serverAuth",
            ],
            check=True,
            capture_output=True,
            env={"PATH": os.defpath},
        )
        cls.hits = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def respond(self):
                cls.hits.append(self.command)
                body = json.dumps({"result": {"summary": {"active_port": 3}}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802 - HTTP server dispatch requires this name
                self.respond()

            def do_POST(self):  # noqa: N802 - HTTP server dispatch requires this name
                self.respond()

            def log_message(self, *args):
                pass

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.certificate, key)
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.stop_server)

    @classmethod
    def stop_server(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        # Keep user proxy, CA, home and account configuration out of the test.
        environment = patch.dict(os.environ, {"NO_PROXY": "localhost,127.0.0.1"}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.hits.clear()
        path = Path(__file__).resolve().parents[1] / "src" / "pikvm_keybow.py"
        tree = ast.parse(path.read_text())
        functions = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in ("get_current_port", "set_port")
        ]
        self.assertEqual(len(functions), 2)
        self.scope = {
            "requests": requests,
            "HTTPBasicAuth": HTTPBasicAuth,
            "PIKVM_HOST": f"https://localhost:{self.server.server_port}",
            "PIKVM_USER": "synthetic-user",
            "PIKVM_PASS": "synthetic-password",
        }
        # Execute only the unchanged API functions, never module/GPIO startup.
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), self.scope)

    def call(self, name, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.scope[name](*args)

    def test_untrusted_certificate_stops_both_requests_before_http(self):
        self.assertIsNone(self.call("get_current_port"))
        self.assertFalse(self.call("set_port", 2))
        self.assertEqual(self.hits, [])

    def test_configured_ca_accepts_both_requests(self):
        os.environ["REQUESTS_CA_BUNDLE"] = str(self.certificate)
        self.assertEqual(self.call("get_current_port"), 3)
        self.assertTrue(self.call("set_port", 2))
        self.assertEqual(self.hits, ["GET", "POST"])

    def test_trusted_certificate_with_wrong_hostname_stops_both_requests(self):
        os.environ["REQUESTS_CA_BUNDLE"] = str(self.certificate)
        self.scope["PIKVM_HOST"] = f"https://127.0.0.1:{self.server.server_port}"
        self.assertIsNone(self.call("get_current_port"))
        self.assertFalse(self.call("set_port", 2))
        self.assertEqual(self.hits, [])


if __name__ == "__main__":
    unittest.main()
