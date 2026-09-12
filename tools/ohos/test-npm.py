#!/usr/bin/env python3
"""Validate installed npm/npx and a signed N-API addon in isolated directories."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('prefix', type=Path, help='unpacked Node distribution')
parser.add_argument('--make', help='native GNU Make executable')
parser.add_argument('--proxy', required=True, help='proxy URL for registry downloads')
args = parser.parse_args()
prefix = args.prefix.resolve()
env = os.environ.copy()
for key in ('NODE_OPTIONS', 'NODE_PATH', 'NODE_TLS_REJECT_UNAUTHORIZED', 'LD_LIBRARY_PATH', 'LD_PRELOAD',
            'CC', 'CXX', 'NODE_OHOS_REAL_CC', 'NODE_OHOS_REAL_CXX',
            'npm_config_nodedir', 'npm_package_config_node_gyp_nodedir'):
    env.pop(key, None)
env['PATH'] = str(prefix / 'bin') + os.pathsep + env['PATH']
for key in ('HTTPS_PROXY', 'HTTP_PROXY', 'https_proxy', 'http_proxy'):
    env[key] = args.proxy
env['NO_PROXY'] = env['no_proxy'] = 'localhost,127.0.0.1,::1'
if args.make:
    env['MAKE'] = args.make

with tempfile.TemporaryDirectory(prefix='node-npm-check-') as temporary:
    root = Path(temporary)
    env['npm_config_cache'] = str(root / 'cache')
    env['npm_config_userconfig'] = str(root / 'user.npmrc')
    env['npm_config_globalconfig'] = str(root / 'global.npmrc')
    env['npm_config_prefix'] = str(root / 'global')
    env['npm_config_registry'] = 'https://registry.npmjs.org/'
    (root / 'user.npmrc').touch()
    (root / 'global.npmrc').touch()

    def run(command, cwd=root):
        print('+ ' + shlex.join(map(str, command)), flush=True)
        subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True, timeout=300)

    node, npm, npx = (prefix / 'bin' / name for name in ('node', 'npm', 'npx'))
    run([node, '--version'])
    run([npm, '--version'])
    run([npx, '--version'])
    run([prefix / 'bin/corepack', '--version'])
    project = root / 'project space'
    project.mkdir()
    (project / 'package.json').write_text(json.dumps({'name': 'ohos-registry-check',
        'version': '1.0.0', 'private': True}))
    run([npm, 'install', '--ignore-scripts', '--no-audit', '--no-fund', 'is-number@7.0.0'], project)
    run([node, '-e', "const a=require('node:assert/strict'); const n=require('is-number'); a.equal(n('42'),true); a.equal(n('NaN'),false); console.log('registry-package-ok');"], project)

    cli = root / 'local-cli'
    cli.mkdir()
    (cli / 'package.json').write_text(json.dumps({'name': 'ohos-local-cli',
        'version': '1.0.0', 'bin': {'ohos-local-cli': 'cli.js'}}))
    (cli / 'cli.js').write_text("#!/usr/bin/env node\nrequire('node:assert/strict').equal(process.argv[2], 'hello world'); console.log('cli-ok:'+process.version);\n")
    (cli / 'cli.js').chmod(0o755)
    run([npm, 'install', '--offline', '--no-audit', '--no-fund', str(cli)], project)
    run([npx, '--offline', '--no', '--', 'ohos-local-cli', 'hello world'], project)
    run([npm, 'install', '--global', '--offline', '--no-audit', '--no-fund', str(cli)])
    run([root / 'global/bin/ohos-local-cli', 'hello world'])
    run([npm, 'uninstall', '--global', '--offline', '--no-audit', '--no-fund', 'ohos-local-cli'])
    assert not (root / 'global/bin/ohos-local-cli').exists()

    addon = root / 'native addon space'
    addon.mkdir()
    (addon / 'package.json').write_text(json.dumps({'name': 'ohos-native-check',
        'version': '1.0.0', 'private': True, 'scripts': {'install': 'node-gyp rebuild'}}))
    (addon / 'binding.gyp').write_text(json.dumps({'targets': [
        {'target_name': 'answer', 'sources': ['answer.c']}]}))
    (addon / 'answer.c').write_text('''#include <node_api.h>
static napi_value answer(napi_env env, napi_callback_info info) {
  napi_value value;
  if (napi_create_int32(env, 42, &value) != napi_ok) return NULL;
  return value;
}
NAPI_MODULE_INIT() {
  napi_value function;
  if (napi_create_function(env, "answer", NAPI_AUTO_LENGTH, answer, NULL, &function) != napi_ok) return NULL;
  if (napi_set_named_property(env, exports, "answer", function) != napi_ok) return NULL;
  return exports;
}
''')
    run([npm, 'install', '--offline', '--no-audit', '--no-fund'], addon)
    run([node, '-e', "require('node:assert/strict').equal(require('./build/Release/answer.node').answer(),42); console.log('native-addon-ok');"], addon)
    print('PASS registry TLS/download, local install, npx, isolated global install/remove, offline signed N-API addon', flush=True)
