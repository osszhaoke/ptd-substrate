"""Offline partner installer. Explicit local choice, never account discovery."""
from pathlib import Path
import argparse
import json
import os
import sys
from zoneinfo import ZoneInfo

APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / 'core')]
from trial_target import Policy, check_data_policy, PERSONAL_IDS, PERSONAL_KEYS
from h1_common import load_instance


def make_config(options, selected_key, data_root):
    root = Path(data_root)
    if not root.is_dir() or root.is_symlink() or not selected_key:
        raise ValueError('TARGET_REQUIRED')
    specs = []
    for option in options:
        row = dict(option)
        if 'root' in row:
            specified = Path(row.pop('root'))
            if specified.is_symlink() or specified.resolve() != (root / row.get('id', '')).resolve():
                raise ValueError('TARGET_ROOT_INVALID')
        directory = root / row.get('id', '')
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError('TARGET_ROOT_INVALID')
        if row.get('kind') not in ('REAL', 'DEMO') or row.get('replay') is not False:
            raise ValueError('TARGET_INVALID')
        if not isinstance(row.get('name'), str) or not row['name'].strip():
            raise ValueError('TARGET_INVALID')
        ZoneInfo(row['tz'])
        ctx = load_instance(directory)
        if (ctx.instance_id, ctx.kind, ctx.tz) != (row['id'], row['kind'], row['tz']):
            raise ValueError('TARGET_METADATA_MISMATCH')
        if row.get('accept') not in (['SYNTHETIC'], ['REAL', 'SYNTHETIC'], ['REAL']):
            raise ValueError('TARGET_INVALID')
        if row.get('default_nature') not in row['accept'] or not isinstance(row.get('cards'), list):
            raise ValueError('TARGET_INVALID')
        check_data_policy(ctx, row)
        specs.append(row)
    config = {'instances': specs, 'band_bridge': False, 'starling': {'enabled': False},
              'device_targets': {name: selected_key for name in ('garmin', 'qkeer', 'somaloop_agent')}}
    policy = Policy.build(config, root)
    if policy.target != selected_key:
        raise ValueError('TARGET_REQUIRED')
    config['instances'] = [row for row in policy.specs(config) if row['key'] == selected_key]
    return config


def write_config(config, path):
    output = Path(path)
    if output.is_symlink() or output.exists() or output.parent.is_symlink() or not output.parent.is_dir():
        raise ValueError('OUTPUT_EXISTS_OR_UNSAFE')
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description='Choose an existing initialized instance folder. No network or account access.')
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        print('本人交互选择后才能生成配置。', file=sys.stderr); return 2
    try:
        key = input('目标实例键：').strip()
        identity = input('目标实例文件夹名称：').strip()
        name = input('页面显示名称：').strip()
        tz = input('时区（例如 Asia/Shanghai）：').strip()
        choice = input('数据性质：1 虚构试用 / 2 本人数据：').strip()
        if choice not in ('1', '2'):
            raise ValueError('TARGET_REQUIRED')
        fictional = choice == '1'
        spec = {'key': key, 'id': identity, 'name': name, 'tz': tz, 'kind': 'DEMO' if fictional else 'REAL',
                'accept': ['SYNTHETIC'] if fictional else ['REAL', 'SYNTHETIC'],
                'default_nature': 'SYNTHETIC' if fictional else 'REAL', 'replay': False, 'cards': []}
        config = make_config([spec], key, args.data_root)
        if input('核对目标与数据性质后，输入 YES 写入配置：').strip() != 'YES':
            print('未写入配置。'); return 2
        write_config(config, args.output)
        print('配置已写入。Oura 需要本人按设备页提示另行配置和授权。'); return 0
    except (ValueError, KeyError, OSError, Exception) as exc:
        # Tool output contains neither personal paths nor input values.
        if getattr(exc, 'code', '') == 'INSTANCE_POLICY_MISMATCH':
            print('未写入配置：所选数据性质与空间不一致。请核对建库时的 --accept。 / Data types differ. Check the --accept option used to create this space.', file=sys.stderr)
        else:
            print('未写入配置：目标或输出位置无效。', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
