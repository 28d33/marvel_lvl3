import json
import os
import time
import uuid
import boto3

dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    endpoint_url=os.environ.get(
        "DYNAMODB_ENDPOINT",
        "http://localhost.localstack.cloud:4566"
    )
)

table = dynamodb.Table(
    os.environ.get("TABLE_NAME", "ChatMessages")
)


def reply(status, data):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "content-type",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        },
        "body": json.dumps(data, default=int)
    }


def handler(event, context):
    try:
        method = event.get("requestContext", {}).get("http", {}).get("method")

        if method == "OPTIONS":
            return reply(200, {})

        body = json.loads(event.get("body") or "{}")
        action = body.get("action")

        if action == "send":
            name = body.get("name", "").strip()
            message = body.get("message", "").strip()

            if not name or not message:
                return reply(400, {
                    "error": "Name and message are required"
                })

            item = {
                "id": str(uuid.uuid4()),
                "room": "main",
                "name": name,
                "message": message,
                "createdAt": int(time.time() * 1000)
            }

            table.put_item(Item=item)

            return reply(200, {
                "success": True,
                "message": item
            })

        if action == "messages":
            result = table.scan()
            messages = result.get("Items", [])
            messages.sort(key=lambda item: int(item["createdAt"]))

            return reply(200, {
                "messages": messages[-100:]
            })

        return reply(400, {
            "error": "Unknown action"
        })

    except Exception as error:
        print("Lambda error:", repr(error))

        return reply(500, {
            "error": str(error)
        })
