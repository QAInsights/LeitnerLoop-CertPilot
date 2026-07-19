import os
import boto3
from datetime import datetime, timedelta, timezone

dynamodb = boto3.resource("dynamodb")

TOPICS_TABLE = os.environ["TOPICS_TABLE"]
PENDING_TABLE = os.environ["PENDING_TABLE"]

# Leitner box number to review interval in days
BOX_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    quiz_id = params.get("quiz_id")
    choice = params.get("choice")

    if not quiz_id or not choice:
        return html_response("Missing quiz_id or choice.")

    pending_table = dynamodb.Table(PENDING_TABLE)
    item = pending_table.get_item(Key={"quiz_id": quiz_id}).get("Item")

    if not item:
        return html_response("This question has expired or was already answered.")

    correct = item["correct"]
    is_correct = choice.upper() == correct.upper()

    update_topic_schedule(item["cert_code"], item["topic"], is_correct)
    pending_table.delete_item(Key={"quiz_id": quiz_id})

    result_text = "Correct!" if is_correct else f"Not quite. Correct answer: {correct}"
    body = f"<h2>{result_text}</h2><p>{item['explanation']}</p>"
    return html_response(body)


def update_topic_schedule(cert_code, topic, is_correct):
    table = dynamodb.Table(TOPICS_TABLE)
    row = table.get_item(Key={"cert_code": cert_code, "topic": topic}).get("Item", {})
    box = row.get("box", 1)

    box = min(box + 1, 5) if is_correct else 1
    interval = BOX_INTERVALS[box]
    next_due = (datetime.now(timezone.utc).date() + timedelta(days=interval)).isoformat()

    table.update_item(
        Key={"cert_code": cert_code, "topic": topic},
        UpdateExpression="SET box = :b, next_due = :n, last_reviewed = :l",
        ExpressionAttributeValues={
            ":b": box,
            ":n": next_due,
            ":l": datetime.now(timezone.utc).date().isoformat(),
        },
    )


def html_response(body_html):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": f"<html><body style='font-family:sans-serif;padding:40px'>{body_html}</body></html>",
    }
