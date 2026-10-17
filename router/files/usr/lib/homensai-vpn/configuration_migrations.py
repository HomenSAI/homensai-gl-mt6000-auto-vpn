"""Versioned private own-config/statistics snapshots, not live UCI migration.

Secrets are preserved only inside the private snapshot; public receipts contain
counts and revision hashes. Native Auto is always disabled on migration/rollback.
"""
import copy
from contextlib import contextmanager
import json
import os
import re
from pathlib import Path
from cascade_executor import Journal, Refused, digest, identity, require


LIMIT = 512*1024


def validate(snapshot):
    require(isinstance(snapshot, dict) and set(snapshot) == {
        'schema', 'main', 'servers', 'statistics'}, 'MIGRATION-SCHEMA')
    require(type(snapshot['schema']) is int and snapshot['schema'] in (1, 2),
            'MIGRATION-VERSION')
    require(isinstance(snapshot['main'], dict) and isinstance(snapshot['statistics'], dict)
            and isinstance(snapshot['servers'], list) and len(snapshot['servers']) <= 16,
            'MIGRATION-CONTENT')
    require(all(isinstance(key,str) and re.fullmatch(r'[A-Za-z0-9_]+',key) and
                (isinstance(value,str) or isinstance(value,list) and all(isinstance(v,str) for v in value))
                for key,value in snapshot['main'].items()), 'MIGRATION-MAIN')
    require(len(json.dumps(snapshot, allow_nan=False).encode()) <= LIMIT,
            'MIGRATION-SIZE')
    seen = set()
    for row in snapshot['servers']:
        require(isinstance(row,dict), 'MIGRATION-SERVER')
        fields = {'profile', 'name', 'channel', 'priority', 'enabled'}
        if snapshot['schema'] == 2:
            fields.add('present')
        if 'section' in row:fields.add('section')
        if 'anonymous' in row:fields.add('anonymous')
        require(isinstance(row, dict) and set(row) == fields, 'MIGRATION-SERVER')
        identity(row['profile'])
        require(row['profile'] not in seen, 'MIGRATION-DUPLICATE')
        seen.add(row['profile'])
        if 'section' in row:
            require(isinstance(row['section'],str) and re.fullmatch(r'[A-Za-z0-9_]{1,80}',row['section']), 'MIGRATION-SECTION')
        if 'anonymous' in row:require(type(row['anonymous']) is bool, 'MIGRATION-SECTION')
        for key in ('name', 'channel'):
            require(isinstance(row[key], str) and 1 <= len(row[key]) <= 64 and
                    all(ord(c) >= 32 for c in row[key]), 'MIGRATION-LABEL')
        if snapshot['schema'] == 1:
            require(isinstance(row['priority'], str) and row['priority'].isascii() and
                    row['priority'].isdigit() and 1 <= int(row['priority']) <= 1000 and
                    row['enabled'] in ('0','1'), 'MIGRATION-LEGACY-VALUE')
        else:
            require(type(row['priority']) is int and 1 <= row['priority'] <= 1000 and
                    type(row['enabled']) is bool and type(row['present']) is bool and
                    (row['present'] or not row['enabled']), 'MIGRATION-CURRENT-VALUE')
    return snapshot


def migrate(snapshot, version, registered):
    validate(snapshot)
    require(type(version) is int and version in (1, 2), 'MIGRATION-VERSION')
    require(isinstance(registered, list) and len(registered) <= 16,
            'MIGRATION-INVENTORY')
    for profile in registered:
        identity(profile)
    require(len(set(registered)) == len(registered), 'MIGRATION-INVENTORY')
    out = copy.deepcopy(snapshot)
    for row in out['servers']:
        enabled = row['enabled'] == '1' if snapshot['schema'] == 1 else row['enabled']
        present = row['profile'] in registered
        row['priority'] = int(row['priority']) if version == 2 else str(row['priority'])
        row['enabled'] = enabled and present if version == 2 else ('1' if enabled and present else '0')
        if version == 2:
            row['present'] = present
        else:
            row.pop('present', None)
    out['schema'] = version
    out['main']['native_enabled'] = '0'
    out['main']['native_until'] = '0'
    out['main']['native_trial'] = ''
    validate(out)
    return out


def from_uci_snapshot(config_name, sections, statistics):
    """Convert a FULL PRIVATE root UCI get_all export, never public inventory.

    No cursor is invoked here. Caller must retain full own-main options to avoid
    replacing a private token with the public inventory's redacted fields.
    """
    require(config_name=='homensai_vpn' and isinstance(sections,list) and
            1<=len(sections)<=17, 'MIGRATION-UCI-CONFIG')
    main=None;servers=[];names=set()
    for section in sections:
        require(isinstance(section,dict), 'MIGRATION-UCI-SECTION')
        name=section.get('.name');kind=section.get('.type')
        require(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_]{1,80}',name) and
                name not in names, 'MIGRATION-UCI-SECTION')
        names.add(name)
        require(all(isinstance(key,str) for key in section), 'MIGRATION-UCI-OPTIONS')
        options={key:copy.deepcopy(value) for key,value in section.items() if not key.startswith('.')}
        require(all(isinstance(key,str) and re.fullmatch(r'[A-Za-z0-9_]+',key) and
                    (isinstance(value,str) or isinstance(value,list) and all(isinstance(v,str) for v in value))
                    for key,value in options.items()), 'MIGRATION-UCI-OPTIONS')
        if kind=='main':
            require(name=='main' and main is None, 'MIGRATION-UCI-MAIN')
            main=options
        elif kind=='server':
            require(set(options)=={'profile','name','channel','priority','enabled'},
                    'MIGRATION-UCI-PARTIAL')
            anonymous=section.get('.anonymous',False)
            require(type(anonymous) is bool or anonymous in ('0','1'), 'MIGRATION-UCI-SECTION')
            options.update(section=name,anonymous=anonymous in (True,'1'))
            servers.append(options)
        else:raise Refused('MIGRATION-UCI-UNKNOWN-SECTION')
    require(main is not None, 'MIGRATION-UCI-MAIN')
    snapshot=dict(schema=1,main=main,servers=servers,statistics=copy.deepcopy(statistics))
    validate(snapshot)
    return snapshot


def to_uci_snapshot(snapshot):
    """Private conversion only. Real application/commit remains NEXT-24."""
    validate(snapshot)
    sections=[dict({'.name':'main','.type':'main'},**copy.deepcopy(snapshot['main']))]
    seen={'main'}
    for row in snapshot['servers']:
        require('section' in row and row['section'] not in seen, 'MIGRATION-SECTION-MISSING')
        seen.add(row['section'])
        sections.append({'.name':row['section'],'.type':'server','.anonymous':row.get('anonymous',False),
                         'profile':row['profile'],'name':row['name'],'channel':row['channel'],
                         'priority':str(row['priority']),
                         'enabled':('1' if row['enabled'] else '0') if snapshot['schema']==2 else row['enabled']})
    return dict(config='homensai_vpn',sections=sections)


class PrivateSnapshotStore:
    """Atomic own-store update with cross-process exclusive lock and CAS.

    Orphaned locks refuse further writes; no automatic lock theft after restart.
    Actual UCI/package migration is separately tested in NEXT-24.
    """
    def __init__(self, directory):
        self.io = Journal(directory)
        self.path = Path(directory)/'configuration.private.json'
        self.backup = Path(directory)/'configuration.previous.private.json'
        self.lock_path = Path(directory)/'configuration.lock'

    @contextmanager
    def locked(self):
        try:
            fd = os.open(str(self.lock_path), os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        except FileExistsError:
            raise Refused('MIGRATION-LOCK-BUSY') from None
        try:
            os.close(fd)
            yield
        finally:
            self.lock_path.unlink()

    @staticmethod
    def envelope(snapshot):
        validate(snapshot)
        return json.dumps(dict(snapshot=snapshot, checksum=digest(snapshot)),
                          sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

    def read(self, path=None):
        path = self.path if path is None else path
        require(path.is_file() and not path.is_symlink(), 'MIGRATION-SNAPSHOT-MISSING')
        require(path.stat().st_size <= LIMIT+1024, 'MIGRATION-SIZE')
        try:
            row = json.loads(path.read_bytes())
            require(set(row) == {'snapshot','checksum'} and
                    digest(row['snapshot']) == row['checksum'], 'MIGRATION-CHECKSUM')
            validate(row['snapshot'])
            return row['snapshot']
        except (KeyError, TypeError, UnicodeError, json.JSONDecodeError):
            raise Refused('MIGRATION-SNAPSHOT-CORRUPT') from None

    def initialize(self, snapshot):
        with self.locked():
            require(not self.path.exists(), 'MIGRATION-ALREADY-INITIALIZED')
            self.io._atomic(self.path, self.envelope(snapshot))

    def commit(self, expected_revision, version, registered):
        with self.locked():
            old = self.read()
            require(digest(old) == expected_revision, 'MIGRATION-EXTERNAL-EDIT')
            candidate = migrate(old, version, registered)
            self.io._atomic(self.backup, self.envelope(old))
            self.io._atomic(self.path, self.envelope(candidate))
            require(digest(self.read()) == digest(candidate), 'MIGRATION-WRITE-UNCONFIRMED')
            return dict(saved=True, schema=version, revision=digest(candidate),
                        server_count=len(candidate['servers']), auto=False)

    def rollback(self, expected_revision, registered):
        with self.locked():
            require(digest(self.read()) == expected_revision, 'MIGRATION-EXTERNAL-EDIT')
            previous = self.read(self.backup)
            candidate = migrate(previous, previous['schema'], registered)
            self.io._atomic(self.path, self.envelope(candidate))
            require(digest(self.read()) == digest(candidate), 'MIGRATION-WRITE-UNCONFIRMED')
            return dict(saved=True, schema=candidate['schema'], revision=digest(candidate), auto=False)
