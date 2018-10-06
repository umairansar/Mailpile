from pgpdump.utils import PgpdumpException
import time
import pgpdump

def _get_creation_time(m):
    """Compatibility shim, for differing versions of pgpdump"""
    try:
        return m.creation_time
    except AttributeError:
        try:
            return m.datetime
        except AttributeError:
            return datetime.datetime(1970, 1, 1, 00, 00, 00)


def get_keydata(data, include_subkeys=False, autocrypt_header=None):
    results = []
    try:
        if "-----BEGIN" in data:
            ak = pgpdump.AsciiData(data)
        else:
            ak = pgpdump.BinaryData(data)
        packets = list(ak.packets())
    except (TypeError, IndexError, PgpdumpException):
        return []

    if autocrypt_header:
        # The autocrypt spec tells us that the visible addr= attribute
        # overrides whatever is on the key itself, so we synthesize a
        # fake UID here so strict e-mail matches don't break Autocrypt.
        default_uids = [{
            'comment': 'Autocrypt',
            'email': autocrypt_header['addr']}]
    else:
        default_uids = []

    now = time.time()
    for m in packets:
        try:
            if isinstance(m, pgpdump.packet.PublicKeyPacket):
                size = str(int(1.024 *
                               round(len('%x' % (m.modulus or 0)) / 0.256)))
                validity = ('e'
                            if (0 < (int(m.expiration_time or 0)) < now)
                            else '')
                results.append({
                    "fingerprint": m.fingerprint,
                    "created": _get_creation_time(m),
                    "validity": validity,
                    "keytype_name": (m.pub_algorithm or '').split()[0],
                    "keysize": size,
                    "uids": default_uids,
                })
            if isinstance(m, pgpdump.packet.UserIDPacket) and results:
                # FIXME: This used to happen with results=[], does that imply
                #        UIDs sometimes come before the PublicKeyPacket?
                results[-1]["uids"].append({"name": m.user_name,
                                            "email": m.user_email})
        except (TypeError, AttributeError, KeyError, IndexError, NameError):
            import traceback
            traceback.print_exc()

    if include_subkeys:
        return results
    else:
        # This will only return keys that have UIDs
        return [k for k in results if k['uids']]
