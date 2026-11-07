"""星簇 · 本机只读 MCP 服务（N12）。不开库、不存数据：每次调用都转给本机 PTDS 进程，由星簇判定并留痕。

    python3 app/mcp_cluster.py          # stdio，JSON-RPC 2.0，一行一条消息

环境变量：PTDS_PORT（默认 8780）、PTDS_KEY（实例 key，必须显式设置）。只连 127.0.0.1。
工具：read_my_vitals {grant_id}
  → POST http://127.0.0.1:$PTDS_PORT/api/cluster/read，头 X-PTDS: 1，体 {"key": $PTDS_KEY, "grant_id": ...}
  → 把返回的 JSON 原文作为工具结果；outcome 不是 READ（DENIED）或 HTTP 出错时 isError = true。
工具：read_my_gene_loci {grant_id, rsids?}
  → 同一个端点，体里多带 "rsids": ["rs4149056", ...]。只认"基因位点"授权；读授权范围外的位点会被拒绝并留痕。

server.py 需要加的端点（集成方实现；全部在 app.lock 里调用，POST 已统一要求 X-PTDS: 1）：
    App.__init__:   self.product_config = json.loads((APP / "web" / "product_config.json").read_text("utf-8"))
    Instance:       self.cluster = ClusterStore(self.ctx.root, app.product_config, tz=self.ctx.tz)
    GET  /api/cluster/list?key=K                 → inst.cluster.list(inst.now())                       [grant, ...]
    GET  /api/cluster/find?key=K&id=G-003        → inst.cluster.find(id, inst.now())  或 404             grant
    GET  /api/cluster/records?key=K[&egress=1]   → inst.cluster.records(inst.snapshot(), egress_only=...) [record, ...]
    POST /api/cluster/create {key, form}         → inst.cluster.create(form, inst.now())                grant
    POST /api/cluster/revoke {key, id}           → inst.cluster.revoke(id, inst.now())                  grant
    POST /api/cluster/read   {key, grant_id}     → inst.cluster.read(grant_id, inst.snapshot(), inst.now(), via="LOCAL_API") # UI/MCP 共用入口，来源由服务端固定
                                                   200 {outcome: READ|DENIED, ...}（拒绝也是 200，已记录）
  H1Error（CLUSTER_FORM_INVALID / CLUSTER_GRANT_UNKNOWN）照现有写法回 400 {error, detail}。
  app.log 只记代码和编号，例如 app.log("cluster_read", inst.ctx.instance_id, grant_id, result["outcome"])。

Claude Desktop（claude_desktop_config.json）或其他 MCP 客户端：
    {"mcpServers": {"ptds": {"command": "python3",
                             "args": ["/绝对路径/app/mcp_cluster.py"],
                             "env": {"PTDS_PORT": "8780", "PTDS_KEY": "PARTNER_KEY"}}}}
Claude Code：claude mcp add ptds -e PTDS_PORT=8780 -e PTDS_KEY=PARTNER_KEY -- python3 /绝对路径/app/mcp_cluster.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

SERVER_INFO = {"name": "ptds-cluster", "version": "0.1.0"}
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
TOOL = {
    "name": "read_my_vitals",
    "description": ("读取本人在 PTDS 里的状态（我的体征 / 关注卡）。只返回这条授权的披露级别允许的内容；"
                    "授权撤销、到期或不存在时被拒绝。每次读取（含被拒绝）都会记进 PTDS 的授权记录。"
                    "结果是关注信号，不构成诊断或治疗建议。"),
    "inputSchema": {"type": "object", "properties": {"grant_id": {
        "type": "string", "description": "星簇授权编号，例如 G-003（在 PTDS 星簇 → 授权规则里看）"}},
        "required": ["grant_id"], "additionalProperties": False},
}
TOOL_GENE = {
    "name": "read_my_gene_loci",
    "description": ("按 rs 号读取本人基因原始数据文件里写着的基因型（染色体、位置、基因型、参考基因组版本、来源文件）。"
                    "需要一条\"基因位点\"授权；授权限定了位点时，只能读这些位点，读别的会被拒绝。每次读取（含被拒绝）都会记进"
                    " PTDS 的授权记录。PTDS 不解读基因型；任何解释都只是遗传倾向，不构成诊断或用药建议。"),
    "inputSchema": {"type": "object", "properties": {
        "grant_id": {"type": "string", "description": "星簇授权编号，例如 G-004（范围是\"基因位点\"的那条）"},
        "rsids": {"type": "array", "items": {"type": "string"}, "maxItems": 50,
                  "description": "要读的 rs 号，例如 [\"rs4149056\"]。不填 = 读授权里列出的全部位点"}},
        "required": ["grant_id"], "additionalProperties": False},
}
TOOLS = {TOOL["name"]: TOOL, TOOL_GENE["name"]: TOOL_GENE}
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 只连本机，忽略代理环境变量


def call_ptds(grant_id: str, rsids=None) -> tuple:
    """返回 (text, is_error)。"""
    port = int(os.environ.get("PTDS_PORT") or 8780)
    key = os.environ.get("PTDS_KEY");
    if not key: return json.dumps({"error": "INSTANCE_UNKNOWN"}), True
    req_body = {"key": key, "grant_id": grant_id}
    if rsids is not None:
        req_body["rsids"] = rsids
    body = json.dumps(req_body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/cluster/read", data=body, method="POST",
                                 headers={"X-PTDS": "1", "Content-Type": "application/json"})
    try:
        with _OPENER.open(req, timeout=20) as r:
            text = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            json.loads(raw)
            return raw, True
        except ValueError:
            return json.dumps({"outcome": "ERROR", "error": f"HTTP_{e.code}"}), True
    except (urllib.error.URLError, OSError):
        return json.dumps({"outcome": "ERROR", "error": "PTDS_UNREACHABLE",
                           "detail": "PTDS 本机进程没有运行，或端口不对"}, ensure_ascii=False), True
    try:
        outcome = json.loads(text).get("outcome")
    except (ValueError, AttributeError):
        return json.dumps({"outcome": "ERROR", "error": "BAD_RESPONSE"}), True
    return text, outcome != "READ"


def handle(msg: dict):
    """一条 JSON-RPC 消息 → 回复（dict）；通知返回 None。"""
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:  # notification（notifications/initialized 等）：不回
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        want = params.get("protocolVersion")
        return ok({"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                   "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER_INFO,
                   "instructions": "PTDS 本机只读接口：用 read_my_vitals（状态卡）或 read_my_gene_loci（基因位点）和授权编号读取。"})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": list(TOOLS.values())})
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            return err(-32602, "Unknown tool: " + str(name))
        args = params.get("arguments") or {}
        grant_id = args.get("grant_id")
        rsids = args.get("rsids") if name == TOOL_GENE["name"] else None
        if not isinstance(grant_id, str) or not grant_id.strip():
            text, is_error = json.dumps({"outcome": "ERROR", "error": "GRANT_ID_REQUIRED"}), True
        elif rsids is not None and not (isinstance(rsids, list) and all(isinstance(x, str) for x in rsids)):
            text, is_error = json.dumps({"outcome": "ERROR", "error": "RSIDS_MUST_BE_LIST_OF_STRINGS"}), True
        else:
            text, is_error = call_ptds(grant_id.strip(), rsids)
        return ok({"content": [{"type": "text", "text": text}], "isError": is_error})
    return err(-32601, "Method not found: " + str(method))


def main() -> None:
    out = sys.stdout.buffer  # UTF-8 regardless of locale
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
            if not isinstance(msg, dict):
                raise ValueError
        except ValueError:  # includes UnicodeDecodeError
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            reply = handle(msg)
        if reply is not None:
            out.write(json.dumps(reply, ensure_ascii=False).encode("utf-8") + b"\n")
            out.flush()


if __name__ == "__main__":
    main()
