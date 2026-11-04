"""Offline subprocess tests: curl is replaced before any provider is invoked."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAKE_CURL = '''#!/usr/bin/env python3
import json, os, pathlib, sys
trace = pathlib.Path(os.environ['CURL_TRACE'])
calls = json.loads(trace.read_text()) if trace.exists() else []
plan = json.loads(os.environ['CURL_PLAN'])
reply = plan[min(len(calls), len(plan)-1)]
calls.append(sys.argv[1:])
trace.write_text(json.dumps(calls))
print(reply.get('body', 'OK') + '\\n' + str(reply.get('status', 200)), end='')
print(reply.get('stderr', ''), file=sys.stderr)
sys.exit(reply.get('exit', 0))
'''
CONFIG = {
    'duckdns': {'DUCKDNS_TOKEN': 'private-token', 'DUCKDNS_DOMAINS': 'one,two'},
    'freedns': {'FREEDNS_TOKEN': 'private-token'},
    'dynu': {'DYNU_PASSWORD': 'private-token', 'DYNU_HOSTNAME': 'host.example.invalid'},
    'desec': {'DESEC_TOKEN': 'private-token', 'DESEC_DOMAINS': 'one.example.invalid,two.example.invalid'},
}


class UpdaterTests(unittest.TestCase):
    def invoke(self, provider='duckdns', config=None, plan=None, overrides=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'curl').write_text(FAKE_CURL)
            (path / 'curl').chmod(0o755)
            env = {
                'PATH': directory + ':' + os.environ['PATH'],
                'DNS_PROVIDER': provider,
                'CURL_TRACE': str(path / 'trace.json'),
                'CURL_PLAN': json.dumps(plan or [{'body': 'OK' if provider == 'duckdns' else 'good'}]),
                **(CONFIG.get(provider, {}) if config is None else config),
                **(overrides or {}),
            }
            result = subprocess.run(['/bin/sh', str(ROOT / 'update_dns.sh')], env=env,
                                    capture_output=True, text=True, timeout=10)
            trace = json.loads((path / 'trace.json').read_text()) if (path / 'trace.json').exists() else []
            self.assertNotIn('private-token', result.stdout + result.stderr)
            return result, trace

    def test_each_provider_performs_a_request(self):
        for provider in CONFIG:
            with self.subTest(provider=provider):
                body = 'Updated host' if provider == 'freedns' else 'OK' if provider == 'duckdns' else 'good 192.0.2.1'
                result, calls = self.invoke(provider, plan=[{'body': body}])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(calls), 1)
                self.assertIn('--connect-timeout', calls[0])
                self.assertIn('--max-time', calls[0])
                self.assertIn('--fail', calls[0])
                self.assertNotIn('--location', calls[0])

    def test_every_required_variable_rejected_before_request(self):
        for provider, config in CONFIG.items():
            for variable in config:
                with self.subTest(provider=provider, missing=variable):
                    result, calls = self.invoke(provider, config={k: v for k, v in config.items() if k != variable})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(calls)

    def test_malformed_lists_fail_before_any_request(self):
        for provider, key in [('duckdns', 'DUCKDNS_DOMAINS'), ('desec', 'DESEC_DOMAINS'), ('freedns', 'FREEDNS_TOKEN')]:
            for value in [',first', 'first,', 'first,,second', 'first, second', 'first\nsecond', 'first\tsecond']:
                with self.subTest(provider=provider, value=value):
                    result, calls = self.invoke(provider, overrides={key: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(calls)

    def test_default_provider(self):
        result, calls = self.invoke(overrides={'DNS_PROVIDER': ''})
        self.assertEqual(result.returncode, 0)
        self.assertIn('https://www.duckdns.org/update', calls[0])

    def test_provider_line_endings(self):
        for provider, body in [('duckdns', 'OK\r\n'), ('dynu', 'good\n'), ('desec', 'good\r\n')]:
            result, _ = self.invoke(provider, plan=[{'body': body}])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_provider(self):
        result, calls = self.invoke('unknown')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(calls)

    def test_transport_and_http_failures_are_redacted(self):
        for reply in [{'exit': 28}, {'exit': 22, 'status': 401}, {'status': 429}, {'status': 302}]:
            with self.subTest(reply=reply):
                result, _ = self.invoke(plan=[{**reply, 'body': 'private-token', 'stderr': 'private-token'}])
                self.assertNotEqual(result.returncode, 0)

    def test_unexpected_provider_response_fails(self):
        for provider in CONFIG:
            result, _ = self.invoke(provider, plan=[{'body': 'private-token'}])
            self.assertNotEqual(result.returncode, 0)

    def test_known_failures(self):
        for provider in ['dynu', 'desec']:
            for body in ['badauth', 'nohost', 'abuse', '911', 'dnserr', '']:
                result, _ = self.invoke(provider, plan=[{'body': body}])
                self.assertNotEqual(result.returncode, 0)

    def test_no_change_is_success(self):
        for provider in ['dynu', 'desec', 'freedns']:
            body = 'ERROR: Address has not changed.' if provider == 'freedns' else 'nochg 192.0.2.1'
            result, _ = self.invoke(provider, plan=[{'body': body}])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_domain_lists_are_single_encoded_arguments(self):
        for provider, variable in [('duckdns', 'DUCKDNS_DOMAINS'), ('desec', 'DESEC_DOMAINS')]:
            result, calls = self.invoke(provider)
            self.assertEqual(result.returncode, 0)
            prefix = 'domains' if provider == 'duckdns' else 'hostname'
            self.assertIn(prefix + '=' + CONFIG[provider][variable], calls[0])

    def test_freedns_multiple_tokens_and_stop_on_failure(self):
        result, calls = self.invoke('freedns', {'FREEDNS_TOKEN': 'first,second'}, [{'body': 'Updated'}])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn('https://sync.afraid.org/u/second/', calls[1])
        result, calls = self.invoke('freedns', {'FREEDNS_TOKEN': 'first,second'}, [{'body': 'ERROR'}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        for tokens in [',first', 'first,', 'first,,second']:
            result, calls = self.invoke('freedns', {'FREEDNS_TOKEN': tokens})
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(calls)

    def test_dynu_group_and_ambiguous_configuration(self):
        result, calls = self.invoke('dynu', {'DYNU_PASSWORD': 'private-token', 'DYNU_GROUP': 'group'})
        self.assertEqual(result.returncode, 0)
        self.assertIn('group=group', calls[0])
        result, calls = self.invoke('dynu', overrides={'DYNU_GROUP': 'group'})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(calls)

    def test_desec_defaults_preserve_ipv6(self):
        result, calls = self.invoke('desec')
        self.assertEqual(result.returncode, 0)
        self.assertIn('--ipv4', calls[0])
        self.assertIn('myipv6=preserve', calls[0])
        self.assertNotIn('myipv4=', calls[0])
        self.assertIn('Authorization: Token private-token', calls[0])

    def test_desec_explicit_addresses(self):
        result, calls = self.invoke('desec', overrides={'DESEC_IPV4': '192.0.2.10', 'DESEC_IPV6': '2001:db8::10'})
        self.assertEqual(result.returncode, 0)
        self.assertIn('myipv4=192.0.2.10', calls[0])
        self.assertIn('myipv6=2001:db8::10', calls[0])

    def test_desec_ipv6_auto_preserves_ipv4(self):
        result, calls = self.invoke('desec', overrides={'DESEC_IPV4': 'preserve', 'DESEC_IPV6': 'auto'})
        self.assertEqual(result.returncode, 0)
        self.assertIn('--ipv6', calls[0])
        self.assertIn('myipv4=preserve', calls[0])

    def test_desec_rejects_empty_and_ambiguous_modes(self):
        for overrides in [{'DESEC_IPV4': ''}, {'DESEC_IPV6': ''}, {'DESEC_IPV6': 'auto'}]:
            result, calls = self.invoke('desec', overrides=overrides)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(calls)


if __name__ == '__main__':
    unittest.main()
