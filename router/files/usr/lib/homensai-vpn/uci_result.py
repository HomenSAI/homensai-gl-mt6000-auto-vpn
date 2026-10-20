"""Expose only fixed UCI writer failure codes, never child/private output."""


def failure_code(result,fallback):
    output=getattr(result,'stdout',b'')
    if type(output) is bytes and output.strip() in (b'SETUP-PENDING-DELTA',b'SETUP-DELTA-UNVERIFIED',b'SETUP-SAVE-UNCONFIRMED'):
        return output.strip().decode('ascii')
    return fallback
