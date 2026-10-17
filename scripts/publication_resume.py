"""Reconcile remote evidence before retrying any publication mutation."""

def finish(ledger,remote,persist):
    def confirmed(action,read,expected):
        try:action()
        except Exception:
            if read()!=expected:raise RuntimeError('PUBLICATION-MUTATION-UNCONFIRMED')
        if read()!=expected:raise RuntimeError('PUBLICATION-MUTATION-UNCONFIRMED')
    current=remote.main()
    if current==ledger['parent']:
        confirmed(remote.push,remote.main,ledger['public'])
    elif current!=ledger['public']:raise ValueError('PUBLICATION-PARENT-MOVED')
    ledger['github_published']=True;persist(ledger)
    tag=ledger.get('planned_release')
    if not tag:return ledger
    current=remote.tag()
    if current is None:confirmed(remote.create_tag,remote.tag,ledger['public'])
    elif current!=ledger['public']:raise ValueError('RELEASE-TAG-COLLISION')
    ledger['tag_verified']=True;persist(ledger)
    release=remote.release()
    if release is None:
        try:remote.create_release()
        except Exception:
            if remote.release() is None:raise RuntimeError('RELEASE-CREATE-UNCONFIRMED')
        release=remote.release()
    if not release or release.get('draft') is not False or release.get('prerelease') is not True:raise ValueError('RELEASE-STATE-MISMATCH')
    ledger['release_verified']=True;persist(ledger)
    for name,sha in remote.expected_assets():
        actual=remote.asset_hash(name)
        if actual is None:
            confirmed(lambda:remote.upload(name),lambda:remote.asset_hash(name),sha)
        elif actual!=sha:raise ValueError('RELEASE-ASSET-COLLISION')
        ledger.setdefault('verified_assets',{})[name]=sha;persist(ledger)
    ledger.update(release=tag,release_download_verified=True,checksum_download_verified=True);persist(ledger)
    return ledger
