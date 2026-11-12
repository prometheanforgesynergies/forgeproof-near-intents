"""No-execution proof: static scan of the package source.

Nothing in this package may contain a code path that can execute a
settlement: no dry=False, no status/submit endpoints, no signing, no
credentials, no wallet handling. If any of these ever appear in
executable code, the build fails here first.

Docstrings and comments that STATE the prohibitions ("no wallet",
"no Authorization header") are stripped before scanning, so the test
judges what the code does, not what it says.
"""
import ast
import io
import os
import sys
import tokenize
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = [
    os.path.join(PKG, "forgeproof_scout.py"),
    os.path.join(PKG, "intents_quote.py"),
    os.path.join(PKG, "demo.py"),
]

# Strings that must never appear ANYWHERE, docs included: a live
# dry=False or an execution endpoint must not even be written down
# as an example.
HARD_BANNED = [
    "dry\": false",
    "dry': false",
    "dry=false",
    "dry = false",
    '"dry": False',
    "'dry': False",
    "dry=False",
    "dry = False",
    "/v0/status",
    "submitdeposit",
    "submit_deposit",
    "signandsend",
    "sign_and_send",
    "processwithdrawal",
    "ft_transfer",
]

# Strings that must never appear in EXECUTABLE code (comments and
# docstrings stripped first).
CODE_BANNED = [
    "authorization",
    "x-api-key",
    "api_key",
    "apikey",
    "private_key",
    "privatekey",
    "mnemonic",
    "seed_phrase",
    "seedphrase",
    "keypair",
    "wallet",
    "bearer",
    "intents-sdk",
    "near-api-js",
]

ALLOWED_IMPORTS = {
    "argparse", "csv", "json", "sys", "datetime", "urllib",
    "urllib.request", "urllib.error",
    "forgeproof_scout", "intents_quote",
}


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _executable_source(path):
    """Source with comments and docstrings removed, via tokenize."""
    tokens = tokenize.generate_tokens(io.StringIO(_read(path)).readline)
    skip = {tokenize.COMMENT, tokenize.STRING}
    # f-string literal text is not executable code either; the
    # expressions inside {} still tokenize separately and stay scanned.
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        if hasattr(tokenize, name):
            skip.add(getattr(tokenize, name))
    kept = []
    for tok in tokens:
        if tok.type in skip:
            continue
        kept.append(tok.string)
    return " ".join(kept)


class TestNoExecution(unittest.TestCase):
    def test_no_hard_banned_strings_anywhere(self):
        for path in SOURCES:
            lowered = _read(path).lower()
            for banned in HARD_BANNED:
                self.assertNotIn(
                    banned.lower(), lowered,
                    f"{os.path.basename(path)} contains banned string: {banned}",
                )

    def test_no_credential_or_wallet_code(self):
        for path in SOURCES:
            code = _executable_source(path).lower()
            for banned in CODE_BANNED:
                self.assertNotIn(
                    banned, code,
                    f"{os.path.basename(path)} executable code contains: {banned}",
                )

    def test_deposit_address_never_sent_or_displayed_as_real(self):
        # The only camelCase "depositAddress" literal allowed is inside
        # the forbidden-field tuple in intents_quote.py.
        for path in SOURCES:
            for lineno, line in enumerate(_read(path).splitlines(), 1):
                if "depositAddress" in line:
                    self.assertIn(
                        "_FORBIDDEN_DRY_FIELDS", line,
                        f"{os.path.basename(path)}:{lineno} uses "
                        f"depositAddress outside the forbidden-field check",
                    )
        # demo.py may only mention a deposit address to say there is none.
        for line in _read(os.path.join(PKG, "demo.py")).splitlines():
            if "deposit address" in line.lower():
                self.assertIn("NONE", line)

    def test_only_one_http_call_site(self):
        code = _executable_source(os.path.join(PKG, "intents_quote.py"))
        self.assertEqual(code.count("urlopen"), 1)
        # Full source names the 1Click host exactly twice: once in the
        # docstring's source citation, once in the API_URL constant.
        source = _read(os.path.join(PKG, "intents_quote.py"))
        self.assertEqual(source.count("chaindefuser.com"), 2)
        for path in (os.path.join(PKG, "forgeproof_scout.py"),
                     os.path.join(PKG, "demo.py")):
            code = _executable_source(path)
            self.assertNotIn("urlopen", code)
            self.assertNotIn("chaindefuser", code)

    def test_import_allowlist(self):
        for path in SOURCES:
            tree = ast.parse(_read(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name, ALLOWED_IMPORTS,
                                      f"{path} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module, ALLOWED_IMPORTS,
                                  f"{path} imports from {node.module}")

    def test_dry_literal_present_and_no_dry_parameter(self):
        source = _read(os.path.join(PKG, "intents_quote.py"))
        self.assertIn('"dry": True', source)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                arg_names = [a.arg for a in node.args.args]
                self.assertNotIn("dry", arg_names,
                                 f"function {node.name} takes a dry parameter")


if __name__ == "__main__":
    unittest.main()
