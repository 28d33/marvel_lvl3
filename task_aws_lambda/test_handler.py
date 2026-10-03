import json, sys, os
from unittest.mock import MagicMock

# mock boto3 before importing handler
mock_table = MagicMock()
mock_table.scan.return_value = {"Items": []}
sys.modules["boto3"] = MagicMock(**{"resource.return_value.Table.return_value": mock_table})

sys.path.insert(0, os.path.dirname(__file__))
import handler

def event(body):
    return {"requestContext": {"http": {"method": "POST"}}, "body": json.dumps(body)}

def check(label, resp, expected_status):
    ok = resp["statusCode"] == expected_status
    print(f"{'✅' if ok else '❌'} {label} → {resp['statusCode']}")
    return ok

results = [
    check("OPTIONS preflight",
        handler.handler({"requestContext": {"http": {"method": "OPTIONS"}}, "body": None}, None), 200),

    check("send valid message",
        handler.handler(event({"action": "send", "name": "Alice", "message": "Hi"}), None), 200),

    check("send missing name",
        handler.handler(event({"action": "send", "name": "", "message": "Hi"}), None), 400),

    check("send blank message",
        handler.handler(event({"action": "send", "name": "Bob", "message": "  "}), None), 400),

    check("get messages",
        handler.handler(event({"action": "messages"}), None), 200),

    check("unknown action",
        handler.handler(event({"action": "delete"}), None), 400),
]

print(f"\n{'✅ All passed' if all(results) else '❌ Some failed'} ({sum(results)}/{len(results)})")
