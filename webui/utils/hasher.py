import hashlib

HASHES = ['md5', 'sha1', 'sha256']

def _hash(data, hash):
    hasher = hashlib.new(hash)
    hasher.update(data)
    return hasher.hexdigest()

def hash(data):
    res = {}
    for h in HASHES:
        res[h] = _hash(data, h)
    res['size'] = len(data)
    return res
