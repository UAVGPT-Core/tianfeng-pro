#!/usr/bin/env python3
"""
VOD BCE v1 签名生成器
======================
用于百度智能云 VOD (v2) API 的鉴权签名。

依赖: bce-python-sdk >= 0.9.72
    pip install bce-python-sdk

用法:
    python3 vod_sign.py <method> <path> [key=val ...]

示例:
    # 查询媒资列表
    python3 vod_sign.py GET /v2/medias status=Running

    # 查询单个媒资
    python3 vod_sign.py GET /v2/medias/<mediaId>

    # 创建媒资 (POST)
    python3 vod_sign.py POST /v2/medias source=BOS key=<bosKey>

输出: 可直接执行的 curl 命令

环境变量:
    BAIDU_AK  — 百度云 Access Key (必须)
    BAIDU_SK  — 百度云 Secret Key (必须)

可选:
    --host <host>     — 默认 vod.bj.baidubce.com
    --expire <秒>     — 签名过期时间，默认 1800
"""

import os, sys, time, hmac, hashlib, urllib.parse
import subprocess

# ====== 引入 SDK normalize_string ======
try:
    from baidubce import utils
except ImportError:
    print("需要 bce-python-sdk: pip install bce-python-sdk", file=sys.stderr)
    sys.exit(1)


# ====== AK/SK ======
# Hardcoded keys removed - GitHub secret scanning blocked push (GH013)
# Must inject via environment variables: BAIDU_AK / BAIDU_SK
AK = os.environ.get("BAIDU_AK")
SK = os.environ.get("BAIDU_SK")
if not AK or not SK:
    print("BAIDU_AK/BAIDU_SK env vars not set", file=sys.stderr)
    sys.exit(1)


# ====== 核心签名函数 ======
def get_canonical_headers(headers, headers_to_sign=None):
    """
    精确模拟 SDK 的 _get_canonical_headers
    - headers_to_sign 默认为 {host, content-md5, content-length, content-type}
    - 所有 key/value 经过 normalize_string（URL 编码特殊字符）
    """
    if headers_to_sign is None or len(headers_to_sign) == 0:
        headers_to_sign = {b"host", b"content-md5", b"content-length", b"content-type"}

    result = []
    hts_lower = {}
    for h in headers_to_sign:
        hb = h if isinstance(h, bytes) else str(h).encode()
        hts_lower[hb.lower().strip()] = h

    for k in headers:
        k_bytes = k if isinstance(k, bytes) else str(k).encode()
        k_lower = k_bytes.lower().strip()
        v = headers[k]
        v_bytes = v if isinstance(v, bytes) else str(v).encode()
        v_stripped = v_bytes.strip()
        if not v_stripped:
            continue
        if k_lower.startswith(b"x-bce-") or k_lower in hts_lower:
            kn = utils.normalize_string(k_lower)
            vn = utils.normalize_string(v_stripped)
            result.append(b"%s:%s" % (kn, vn))
    result.sort()
    return b"\n".join(result)


def make_auth(method, path, params, host, ak, sk, now_ts=None, expire_s=1800):
    """
    生成 BCE v1 签名字符串

    参数:
        method: "GET" | "POST" | "PUT" | "DELETE"
        path:   "/v2/medias"
        params: {"status": "Running"} 或 {}
        host:   "vod.bj.baidubce.com"
        ak, sk: 访问密钥
        now_ts: 可选，当前时间戳
        expire_s: 签名过期秒数

    返回:
        (timestamp_str, auth_string)
    """
    if now_ts is None:
        now_ts = int(time.time())

    ct = utils.get_canonical_time(now_ts)
    sk_info = b"bce-auth-v1/%s/%s/%d" % (ak.encode(), ct, expire_s)
    sign_key = hmac.new(sk.encode(), sk_info, hashlib.sha256).hexdigest()

    qs = utils.get_canonical_querystring(params, True)

    headers = {b"Host": host.encode(), b"x-bce-date": ct}
    ch = get_canonical_headers(headers)

    stb = b"\n".join([
        method.encode(),
        path.encode(),
        qs,
        ch,
    ])

    sig = hmac.new(sign_key.encode(), stb, hashlib.sha256).hexdigest()
    hts = b";".join(sorted(k.lower().strip() for k in headers.keys()))
    auth = b"%s/%s/%s" % (sk_info, hts, sig.encode())

    return ct.decode(), auth.decode()


# ====== CLI ======
def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    method = args[0].upper()
    path = args[1]

    host = "vod.bj.baidubce.com"
    expire = 1800
    params = {}

    for arg in args[2:]:
        if arg == "--host" and args.index(arg) + 1 < len(args):
            host = args[args.index(arg) + 1]
        elif arg.startswith("--expire="):
            expire = int(arg.split("=", 1)[1])
        elif "=" in arg:
            k, v = arg.split("=", 1)
            params[k] = v

    now_ts = int(time.time())
    ct_str, auth_str = make_auth(method, path, params, host, AK, SK, now_ts, expire)

    # Build URL
    if params:
        url = f"https://{host}{path}?{urllib.parse.urlencode(params)}"
    else:
        url = f"https://{host}{path}"

    print(f"# 签名时间: {ct_str}")
    print(f"# 过期时间: {expire}s")
    print(f"# Authorization: {auth_str}")
    print()
    print(f"curl -v '{url}' \\")
    for hdr in ["Host", "x-bce-date"]:
        val = host if hdr == "Host" else ct_str
        print(f"  -H '{hdr}: {val}' \\")
    print(f"  -H 'Authorization: {auth_str}'")


if __name__ == "__main__":
    main()
