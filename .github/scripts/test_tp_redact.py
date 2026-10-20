"""Redaction keeps credential-shaped model output out of published text."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tp_check
import tp_redact
import tp_review
from test_tp_gate import PR, SHA, assessment, scoring_fixture
from tp_hooks import TestPlanHooks

GITHUB_TOKEN = 'ghp_' + 'x' * 36
JWT = 'eyJ' + 'A' * 24 + '.eyJ' + 'B' * 24 + '.' + 'C' * 16
PEM = ('-----BEGIN ' + 'RSA PRIVATE KEY-----\n'
       'MIIEowIBAAKCAQEAfakekeymaterial1234\n'
       '-----END ' + 'RSA PRIVATE KEY-----')


class RedactionPatternTests(unittest.TestCase):
    def test_private_key_blocks_are_redacted(self):
        redacted = tp_redact.redact(f'leaked key:\n{PEM}\nafter')
        self.assertNotIn('fakekeymaterial', redacted)
        self.assertNotIn('BEGIN', redacted)
        self.assertIn(tp_redact.REDACTED, redacted)
        self.assertIn('leaked key:', redacted)
        self.assertIn('after', redacted)

    def test_authorization_and_bearer_values_are_redacted(self):
        self.assertEqual(
            tp_redact.redact('Authorization: Bearer abcdef'),
            'Authorization: ' + tp_redact.REDACTED,
        )
        self.assertEqual(
            tp_redact.redact('bearer ' + 'A' * 30 + ' accepted'),
            'bearer ' + tp_redact.REDACTED + ' accepted',
        )

    def test_provider_credentials_are_redacted(self):
        for prefix in ('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_'):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    tp_redact.redact(prefix + 'x' * 36),
                    tp_redact.REDACTED,
                )
        self.assertEqual(tp_redact.redact('git' + 'hub_pat_' + 'x' * 30),
                         tp_redact.REDACTED)
        for prefix in ('AKIA', 'ASIA'):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    tp_redact.redact(prefix + '0123456789ABCDEF'),
                    tp_redact.REDACTED,
                )
        self.assertEqual(tp_redact.redact('AIza' + 'a' * 35),
                         tp_redact.REDACTED)
        for prefix in ('xoxa-', 'xoxb-', 'xoxp-', 'xoxr-', 'xoxs-'):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    tp_redact.redact(prefix + '1234567890-ABCDEF'),
                    tp_redact.REDACTED,
                )

    def test_jwt_is_redacted(self):
        redacted = tp_redact.redact(f'session {JWT} persisted')
        self.assertNotIn('eyJ', redacted)
        self.assertIn(tp_redact.REDACTED, redacted)

    def test_sensitive_assignments_redact_only_values(self):
        for source, expected in (
            (f'password=hunter2', 'password=' + tp_redact.REDACTED),
            (f'"secret": "s3cr3t-value"',
             '"secret": "' + tp_redact.REDACTED + '"'),
            (f'api_key: ABC123', 'api_key: ' + tp_redact.REDACTED),
            (f'client_secret: oauth-value',
             'client_secret: ' + tp_redact.REDACTED),
            (f'aws_secret_access_key: wJalrXUtnFEMI',
             'aws_secret_access_key: ' + tp_redact.REDACTED),
            (f'client-key-data: LS0tLS1CRUdJTi',
             'client-key-data: ' + tp_redact.REDACTED),
            (f'client-certificate-data: LS0tLS1CRUdJ',
             'client-certificate-data: ' + tp_redact.REDACTED),
            (f'certificate-authority-data: LS0tLS1CRUd',
             'certificate-authority-data: ' + tp_redact.REDACTED),
            (f'token: {JWT}', 'token: ' + tp_redact.REDACTED),
        ):
            with self.subTest(source=source):
                self.assertEqual(tp_redact.redact(source), expected)

    def test_email_addresses_are_redacted(self):
        redacted = tp_redact.redact('contact user.name+tag@example.com now')
        self.assertNotIn('example.com', redacted)
        self.assertIn(tp_redact.REDACTED, redacted)
        self.assertIn('contact', redacted)


class PlanTextSurvivesRedactionTests(unittest.TestCase):
    def test_normal_plan_evidence_is_unchanged(self):
        unchanged = (
            'Commit f6dbd636792f16489dde9f5504ccc4ade2146f9a pins the plan. '
            'TC-FR4-01 covers osac-operator/internal/controller/foo.go:100-160 '
            'and proto/private/v1/volumes.proto. '
            '**Tokens:** 100 in / 50 out. '
            'See https://github.com/osac-project/osac/pull/375 and '
            'https://redhat.atlassian.net/browse/OSAC-4542. '
            'The rubric tokenizes each clause; authorization is delegated to OPA; '
            'the bearer of tokens is the tenant. '
            'Short prefixes like AKIA123 and AIza1 and xoxb-abc stay readable.'
        )
        self.assertEqual(tp_redact.redact(unchanged), unchanged)

    def test_redaction_is_idempotent(self):
        once = tp_redact.redact(f'password=hunter2 {GITHUB_TOKEN}')
        self.assertEqual(tp_redact.redact(once), once)


class RedactJsonTests(unittest.TestCase):
    def test_strings_are_redacted_recursively(self):
        value = {
            'summary': f'uses {GITHUB_TOKEN}',
            'findings': {'suggestions': [f'email admin@example.com', 'clean']},
            'scores': {'grounding': 2},
            'nested': [{'note': 'password=hunter2'}],
        }
        redacted = tp_redact.redact_json(value)
        self.assertNotIn(GITHUB_TOKEN, json.dumps(redacted))
        self.assertNotIn('example.com', json.dumps(redacted))
        self.assertNotIn('hunter2', json.dumps(redacted))
        self.assertEqual(redacted['scores'], {'grounding': 2})
        self.assertEqual(redacted['findings']['suggestions'][1], 'clean')
        self.assertIn('scores', redacted)


class RedactionEndToEndTests(unittest.TestCase):
    def test_model_secrets_never_reach_artifacts_comments_or_check_summary(self):
        value = assessment()
        value['summary'] = f'Admin token {GITHUB_TOKEN} in evidence'
        value['feedback'] = f'password: hunter2 and {JWT}'
        value['criterionNotes']['grounding'] = 'contact admin@example.com'
        value['findings']['suggestions'] = [f'bearer {GITHUB_TOKEN}']
        leaked = (GITHUB_TOKEN, 'hunter2', JWT, 'admin@example.com')
        with scoring_fixture() as skills, tempfile.TemporaryDirectory() as directory:
            hooks = TestPlanHooks(
                repo='test/repo', skills_path=str(skills),
                pr_data=dict(testplan_content='plan', design_content='design',
                             prd_content='prd'),
            )
            with patch.object(
                tp_review, 'complete', return_value=(json.dumps(value), {}),
            ), patch.object(
                tp_review, 'get_pull_request', return_value=PR,
            ), patch.object(
                hooks, '_gh', return_value='',
            ), patch.object(hooks, '_upsert_score_comment') as upsert:
                tp_review.run_review(hooks, 'test-plan-score', 'TP-42',
                                     {'number': 42, 'headRefOid': SHA},
                                     directory, model='test')
            for name in ('assessment.json', 'verdict.json'):
                artifact = (Path(directory) / name).read_text()
                self.assertIn(tp_redact.REDACTED, artifact)
                for secret in leaked:
                    self.assertNotIn(secret, artifact)
            body = upsert.call_args.args[1]
            self.assertIn('REDACTED', body)
            for secret in leaked:
                self.assertNotIn(secret, body)
            report = {'head_sha': SHA, 'plans': [json.loads(
                (Path(directory) / 'verdict.json').read_text())]}
            report['plans'][0]['path'] = 'enhancements/one/testplan.md'
            summary = tp_check.report_summary(report)
            self.assertIn('REDACTED', summary)
            for secret in leaked:
                self.assertNotIn(secret, summary)


if __name__ == '__main__':
    unittest.main()
