"""ArchivesSpace のバックエンド API を呼ぶ（評価の道具で使う）。

接続先と利用者は環境変数 ASPACE_API・ASPACE_USER・ASPACE_PASSWORD で指定する（既定は手元の試験環境の初期値）。
"""

import json
import os
import urllib.error
import urllib.request

API = os.environ.get("ASPACE_API", "http://localhost:8090/staff/api")
USER = os.environ.get("ASPACE_USER", "admin")
PASSWORD = os.environ.get("ASPACE_PASSWORD", "admin")


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-ArchivesSpace-Session", token)
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as err:
        # 何が弾かれたか分かるように、応答の本文を添える
        err.body = err.read().decode()
        err.msg = f"{err.msg}: {method} {path}: {err.body[:500]}"
        raise


def login():
    req = urllib.request.Request(
        f"{API}/users/{USER}/login?password={PASSWORD}", method="POST"
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())["session"]
