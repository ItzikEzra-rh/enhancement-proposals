"""Redaction keeps credential-shaped model output out of published text."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import tp_check
import tp_hooks
import tp_redact
import tp_review
from test_tp_gate import (PR, SHA, assessment, scoring_fixture,
                          working_directory)
from tp_hooks import TestPlanHooks

FAKE_GH_TOKEN = 'gh' + 'p_' + 'x' * 36
FIXTURE_JWT = 'ey' + 'J' + 'A' * 24 + '.ey' + 'J' + 'B' * 24 + '.' + 'C' * 16
FIXTURE_PEM = ('-----BEGIN ' + 'RSA PRIVATE KEY-----\n'
               'MIIEowIBAAKCAQEAfakekeymaterial1234\n'
               '-----END ' + 'RSA PRIVATE KEY-----')
FAKE_SSN = '12' + '3-45-' + '6789'
FAKE_CARD = '4111' + ' 1111' + ' 1111' + ' 1111'
FAKE_CARD_DASHES = '4111' + '-1111' + '-1111' + '-1111'


class RedactionPatternTests(unittest.TestCase):
    def test_private_key_blocks_are_redacted(self):
        redacted = tp_redact.redact(f'leaked key:\n{FIXTURE_PEM}\nafter')
        self.assertNotIn('fakekeymaterial', redacted)
        self.assertNotIn('BEGIN', redacted)
        self.assertIn(tp_redact.REDACTED, redacted)
        self.assertIn('leaked key:', redacted)
        self.assertIn('after', redacted)

    def test_authorization_and_bearer_values_are_redacted(self):
        self.assertEqual(
            tp_redact.redact('Authorization: Basic ' + 'dXNl' + 'cjpwYXNz'),
            'Authorization: Basic ' + tp_redact.REDACTED,
        )
        self.assertEqual(
            tp_redact.redact('authorization: Bearer ' + 'A' * 24),
            'authorization: Bearer ' + tp_redact.REDACTED,
        )
        self.assertEqual(
            tp_redact.redact('Authorization: ' + 'K' * 40),
            'Authorization: ' + tp_redact.REDACTED,
        )
        self.assertEqual(
            tp_redact.redact('bearer ' + 'A' * 30 + ' accepted'),
            'bearer ' + tp_redact.REDACTED + ' accepted',
        )

    def test_authorization_prose_survives(self):
        for prose in (
            '**Authorization:** tenant admin only',
            'Authorization: requires Cloud Provider Admin role',
            '| Authorization: | 403 for non-owners |',
            'Authorization: Basic auth is not used here',
        ):
            with self.subTest(prose=prose):
                self.assertEqual(tp_redact.redact(prose), prose)

    def test_provider_credentials_are_redacted(self):
        for prefix in tuple('gh' + char + '_' for char in 'pousr'):
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
        redacted = tp_redact.redact(f'session {FIXTURE_JWT} persisted')
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
            (f'token: {FIXTURE_JWT}', 'token: ' + tp_redact.REDACTED),
        ):
            with self.subTest(source=source):
                self.assertEqual(tp_redact.redact(source), expected)

    def test_identifier_prefixed_keys_are_redacted(self):
        for source, expected in (
            ('ACCESS_TOKEN=abc123', 'ACCESS_TOKEN=' + tp_redact.REDACTED),
            ('access_token: val-1', 'access_token: ' + tp_redact.REDACTED),
            ('refresh_token: r-tok-987', 'refresh_token: ' + tp_redact.REDACTED),
            ('FAKE_GH_TOKEN=' + FAKE_GH_TOKEN,
             'FAKE_GH_TOKEN=' + tp_redact.REDACTED),
            ('db_password=hunter2', 'db_password=' + tp_redact.REDACTED),
            ('DB_PASSWORD=hunter2', 'DB_PASSWORD=' + tp_redact.REDACTED),
            ('aws_session_token=XYZabc',
             'aws_session_token=' + tp_redact.REDACTED),
            ('authToken: abc123xyz', 'authToken: ' + tp_redact.REDACTED),
            ('"access_token": "val-1"',
             '"access_token": "' + tp_redact.REDACTED + '"'),
        ):
            with self.subTest(source=source):
                self.assertEqual(tp_redact.redact(source), expected)
        self.assertEqual(tp_redact.redact('the access token is rotated'),
                         'the access token is rotated')

    def test_us_ssn_is_redacted(self):
        self.assertEqual(tp_redact.redact(f'ssn {FAKE_SSN} on file'),
                         'ssn ' + tp_redact.REDACTED + ' on file')
        # A phone number formatted exactly like an SSN is redacted too:
        # over-redacting that format is safer than leaking a real SSN.
        self.assertEqual(tp_redact.redact('call 555-12-3456'),
                         'call ' + tp_redact.REDACTED)
        for invalid in ('000-45-6789', '666-45-6789', '900-12-3456',
                        '123-00-6789', '123-45-0000'):
            with self.subTest(invalid=invalid):
                self.assertEqual(tp_redact.redact(f'seen {invalid}'),
                                 f'seen {invalid}')

    def test_payment_cards_are_redacted_only_when_luhn_valid(self):
        self.assertEqual(tp_redact.redact(f'card {FAKE_CARD} charged'),
                         'card ' + tp_redact.REDACTED + ' charged')
        self.assertEqual(tp_redact.redact(f'card {FAKE_CARD_DASHES} charged'),
                         'card ' + tp_redact.REDACTED + ' charged')
        invalid = '4111' + ' 1111' + ' 1111' + ' 1112'
        self.assertEqual(tp_redact.redact(f'id {invalid} kept'),
                         f'id {invalid} kept')

    def test_session_and_cookie_values_are_redacted(self):
        self.assertEqual(tp_redact.redact('session_id: abc123xyz'),
                         'session_id: ' + tp_redact.REDACTED)
        self.assertEqual(tp_redact.redact('sessionId: value1'),
                         'sessionId: ' + tp_redact.REDACTED)
        self.assertEqual(tp_redact.redact('sid: sess-123'),
                         'sid: ' + tp_redact.REDACTED)
        self.assertEqual(
            tp_redact.redact('X-Session-Token: ' + 'A' * 30),
            'X-Session-Token: ' + tp_redact.REDACTED)
        cookie_value = 'B' * 20
        self.assertEqual(
            tp_redact.redact(f'Cookie: sessionid={cookie_value}; theme=dark'),
            'Cookie: sessionid=' + tp_redact.REDACTED + '; theme=dark')
        self.assertEqual(
            tp_redact.redact(f'Set-Cookie: session={cookie_value}'),
            'Set-Cookie: session=' + tp_redact.REDACTED)
        self.assertEqual(tp_redact.redact('Cookie: not used in this release'),
                         'Cookie: not used in this release')

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
            'Dates 2026-10-20 and runs 2026-10-20 2026-10-21 stay readable. '
            'The service endpoint fulfillment-service.osac.svc:8443 and '
            'keycloak.keycloak.svc.cluster.local are hostnames, not secrets. '
            'See https://github.com/osac-project/osac/pull/375 and '
            'https://redhat.atlassian.net/browse/OSAC-4542. '
            'The rubric tokenizes each clause; authorization is delegated to OPA; '
            'the bearer of tokens is the tenant. '
            'Short prefixes like AKIA123 and AIza1 and xoxb-abc stay readable.'
        )
        self.assertEqual(tp_redact.redact(unchanged), unchanged)

    def test_redaction_is_idempotent(self):
        once = tp_redact.redact(f'password=hunter2 {FAKE_GH_TOKEN}')
        self.assertEqual(tp_redact.redact(once), once)

    def test_keyed_rule_stops_at_the_first_value_token(self):
        # Prose after a sensitive key loses at most its first word; the
        # rest of the sentence stays readable.
        self.assertEqual(
            tp_redact.redact('secret: must be stored in a Secret'),
            'secret: ' + tp_redact.REDACTED + ' be stored in a Secret',
        )
        self.assertEqual(
            tp_redact.redact('token: required'),
            'token: ' + tp_redact.REDACTED,
        )
        self.assertEqual(tp_redact.redact('password field is masked'),
                         'password field is masked')


class RedactJsonTests(unittest.TestCase):
    def test_strings_are_redacted_recursively(self):
        value = {
            'summary': f'uses {FAKE_GH_TOKEN}',
            'findings': {'suggestions': [f'email admin@example.com', 'clean']},
            'scores': {'grounding': 2},
            'nested': [{'note': 'password=hunter2'}],
        }
        redacted = tp_redact.redact_json(value)
        self.assertNotIn(FAKE_GH_TOKEN, json.dumps(redacted))
        self.assertNotIn('example.com', json.dumps(redacted))
        self.assertNotIn('hunter2', json.dumps(redacted))
        self.assertEqual(redacted['scores'], {'grounding': 2})
        self.assertEqual(redacted['findings']['suggestions'][1], 'clean')
        self.assertIn('scores', redacted)


class RedactionEndToEndTests(unittest.TestCase):
    def test_report_summary_redacts_raw_values_before_escaping(self):
        fake_token = 'gh' + 'p_' + 'y' * 36
        report = {
            'head_sha': 'a' * 40,
            'plans': [{'path': 'enhancements/one/testplan.md', 'total': 8,
                       'verdict': 'Revise',
                       'feedback': f'leaked {fake_token} by admin@example.com'}],
            'error': f'mail user@example.com with {fake_token}',
        }
        summary = tp_check.report_summary(report)
        self.assertNotIn(fake_token, summary)
        self.assertNotIn('example.com', summary)
        self.assertNotIn('&#64;', summary)
        self.assertNotIn('@', summary)
        self.assertIn('REDACTED', summary)

    def test_replacement_values_are_redacted_and_anchors_still_apply(self):
        fake_token = 'gh' + 'p_' + 'z' * 36
        original = 'front matter\n### FR4\nold result\n### FR5\n'
        revised = tp_review.apply_response_replacements(original, {
            'replacements': [
                {'old': 'old result', 'new': f'specific result citing {fake_token}'},
                {'old': '### FR5\n', 'new': 'additional case\n### FR5\n'},
            ],
        })
        self.assertNotIn(fake_token, revised)
        self.assertIn(tp_redact.REDACTED, revised)
        self.assertIn('specific result citing', revised)
        self.assertIn('additional case\n### FR5\n', revised)
        self.assertIn('front matter', revised)

    def test_respond_preserves_author_text_and_redacts_model_edits(self):
        fake_token = 'gh' + 'p_' + 'z' * 36
        output = json.dumps({'replacements': [
            {'old': 'old result', 'new': f'new evidence citing {fake_token}'},
        ]})
        plan = ('owner@example.com\n' + 'planning context line\n' * 40
                + '### FR4\nold result\n')
        hooks = TestPlanHooks(repo='test/repo', skills_path='unused',
                              pr_data={'testplan_content': plan})
        with tempfile.TemporaryDirectory() as directory, patch.object(
            hooks, '_gh', return_value='',
        ), patch.object(
            tp_review, 'complete', return_value=(output, {}),
        ), patch.object(
            tp_review, 'get_pull_request', return_value=PR,
        ), patch.object(hooks, 'apply_labels') as publish:
            tp_review.run_review(hooks, 'test-plan-review', 'TP-42',
                                 {'number': 42, 'headRefOid': SHA}, directory,
                                 model='test')
            publish.assert_called_once()
            revision = (Path(directory) / 'testplan-output.md').read_text()
        self.assertIn('owner@example.com', revision)
        self.assertIn('new evidence citing', revision)
        self.assertNotIn(fake_token, revision)
        self.assertIn(tp_redact.REDACTED, revision)

    def test_generate_pr_gets_a_redacted_plan(self):
        fake_token = 'gh' + 'p_' + 'g' * 36
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'testplan-output.md'
            output.write_text('# Test Plan\n\nEvidence uses ' + fake_token + '\n')
            hooks = TestPlanHooks(repo='test/repo', skills_path='unused',
                                  shadow=False)
            with patch.object(
                hooks, '_gh', return_value='',
            ), patch.object(
                tp_hooks.subprocess, 'run',
            ) as run, working_directory(directory):
                hooks.apply_labels('TP-42', {}, 'generate', directory,
                                   ticket={'_ep_slug': 'osac-1',
                                           'title': 'Test title'})
            self.assertTrue(run.called)
            dest = Path(directory) / 'enhancements/osac-1/TestPlan.md'
            content = dest.read_text()
            self.assertNotIn(fake_token, content)
            self.assertIn(tp_redact.REDACTED, content)
            self.assertIn('# Test Plan', content)

    def test_model_secrets_never_reach_artifacts_comments_or_check_summary(self):
        value = assessment()
        value['summary'] = f'Admin token {FAKE_GH_TOKEN} in evidence'
        value['feedback'] = f'password: hunter2 and {FIXTURE_JWT}'
        value['criterionNotes']['grounding'] = 'contact admin@example.com'
        value['findings']['suggestions'] = [f'bearer {FAKE_GH_TOKEN}']
        leaked = (FAKE_GH_TOKEN, 'hunter2', FIXTURE_JWT, 'admin@example.com')
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


class ErrorLoggingRedactionTests(unittest.TestCase):
    def capture_stderr(self):
        stream = io.StringIO()
        return stream, contextlib.redirect_stderr(stream)

    def test_review_exception_is_redacted_before_logging(self):
        # IN_CI is read from GITHUB_ACTIONS when the module is imported;
        # patch the constant so the CI exit contract is deterministic.
        error = RuntimeError(f'provider failed with {FAKE_GH_TOKEN}')
        files = [{'filename': 'enhancements/one/testplan.md',
                  'status': 'modified'}]
        with patch.dict(os.environ, {'PR_NUMBER': '42'}), patch.object(
            tp_review, 'IN_CI', True,
        ), patch.object(
            tp_review, 'get_pull_request', return_value=PR,
        ), patch.object(
            tp_review, 'get_changed_files', return_value=files,
        ), patch.object(
            tp_review, 'fetch_pr_file', return_value=None,
        ), patch.object(
            tp_review, 'fetch_pr_documents',
            return_value={'head_repo': tp_review.REPO},
        ), patch.object(
            tp_review, 'run_review', side_effect=error,
        ):
            stream, redirect = self.capture_stderr()
            with redirect:
                with self.assertRaises(SystemExit) as raised:
                    tp_review.respond_main()
        self.assertEqual(raised.exception.code, 1)
        self.assertNotIn(FAKE_GH_TOKEN, stream.getvalue())
        self.assertIn(tp_redact.REDACTED, stream.getvalue())

    def test_score_exception_is_redacted_in_log_and_report(self):
        error = RuntimeError(f'scoring failed with {FAKE_GH_TOKEN}')
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {'PR_NUMBER': '42', 'PR_HEAD_SHA': SHA,
                         'GITHUB_STEP_SUMMARY': ''},
        ), patch.object(tp_review, 'get_pull_request', side_effect=error):
            stream, redirect = self.capture_stderr()
            with redirect, working_directory(directory):
                result = tp_review.score_main()
            report = json.loads(
                (Path(directory) / 'test-plan-score' / 'report.json').read_text())
        self.assertEqual(result, 1)
        self.assertNotIn(FAKE_GH_TOKEN, stream.getvalue())
        self.assertIn(tp_redact.REDACTED, stream.getvalue())
        self.assertNotIn(FAKE_GH_TOKEN, report['error'])
        self.assertIn(tp_redact.REDACTED, report['error'])

    def test_gh_error_text_is_redacted_before_logging(self):
        failure = Mock(returncode=1,
                       stderr=f'request failed with {FAKE_GH_TOKEN}')
        hooks = TestPlanHooks(repo='test/repo', skills_path='unused')
        with patch.object(tp_hooks.subprocess, 'run', return_value=failure):
            stream, redirect = self.capture_stderr()
            with redirect:
                hooks._gh(['pr', 'view', '42'], check=False)
            with self.assertRaises(RuntimeError) as raised:
                hooks._gh(['pr', 'view', '42'], check=True)
        self.assertNotIn(FAKE_GH_TOKEN, stream.getvalue())
        self.assertIn(tp_redact.REDACTED, stream.getvalue())
        self.assertNotIn(FAKE_GH_TOKEN, str(raised.exception))
        self.assertIn(tp_redact.REDACTED, str(raised.exception))

    def test_truncation_happens_after_redaction(self):
        # A token straddling the truncation boundary must not survive as
        # a partial fragment: redact the complete stderr first.
        fake_edge_token = 'gh' + 'p_' + 'e' * 36
        fragments = [fake_edge_token[i:i + 8]
                     for i in range(len(fake_edge_token) - 7)]
        # The token is preceded by a space so the word boundary the
        # token patterns anchor on exists; glued to word characters a
        # token is deliberately not matched (that is what keeps paths
        # and identifiers readable).
        failure = Mock(returncode=1, stderr='a' * 291 + ' ' + fake_edge_token)
        with patch.object(tp_review.subprocess, 'run', return_value=failure):
            with self.assertRaises(RuntimeError) as raised:
                tp_review.gh(['pr', 'view', '42'])
        message = str(raised.exception)
        self.assertIn('a' * 291, message)
        for fragment in fragments:
            self.assertNotIn(fragment, message)

        failure = Mock(returncode=1, stderr='b' * 191 + ' ' + fake_edge_token)
        hooks = TestPlanHooks(repo='test/repo', skills_path='unused')
        with patch.object(tp_hooks.subprocess, 'run', return_value=failure):
            with self.assertRaises(RuntimeError) as raised:
                hooks._gh(['pr', 'view', '42'], check=True)
        message = str(raised.exception)
        self.assertIn('b' * 191, message)
        for fragment in fragments:
            self.assertNotIn(fragment, message)


if __name__ == '__main__':
    unittest.main()
