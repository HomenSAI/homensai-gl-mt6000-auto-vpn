"""Publish completed website measurements without refreshing channel health."""
from website_response import METRIC,TARGET_SET


def publish_completed(status,pair,settings,sampler,history,write_status,read_native,now):
    """Monitor-thread only; no sockets, commands, or extra flash checkpoints.

    The health snapshot, scan ID and profile timestamps retain their original
    meaning. Copy before writing so a failed RAM write remains retryable. The
    history deduplicates by the original per-channel measurement timestamp.
    """
    if sampler.closed or sampler.paused():return status
    profiles=[dict(row) for row in status['profiles']]
    changed=sampler.collect(profiles,pair,now)
    if not changed and getattr(history,'_publication_pending',False) is not True:return status
    updated=dict(status,profiles=profiles)
    # Only an outstanding publication failure needs retries without a new
    # sample. Keep this monitor-local flag through a failed RAM write as well.
    history._publication_pending=True
    history_ok=False
    try:
        history.observe(dict(updated,native_failover=read_native()),settings,now)
        updated['website_response_history']=history.public(now)
        history_ok=True
    except Exception:
        updated['website_response_history']={'metric':METRIC,'target_set':TARGET_SET,
            'rows':[],'coverage_rows':[],'notice':'WEBSITE-HISTORY-UNAVAILABLE'}
    if updated!=status:write_status(updated)
    history._publication_pending=not history_ok
    return updated
