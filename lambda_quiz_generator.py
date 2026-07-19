import json
import os
import random
import string
import time
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime")
ses = boto3.client("ses")

TOPICS_TABLE = os.environ["TOPICS_TABLE"]
PENDING_TABLE = os.environ["PENDING_TABLE"]
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]
API_BASE_URL = os.environ["API_BASE_URL"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
QUESTIONS_PER_EMAIL = int(os.environ.get("QUESTIONS_PER_EMAIL", "10"))
QUESTIONS_PER_TOPIC = int(os.environ.get("QUESTIONS_PER_TOPIC", "2"))

CERT_NAMES = {
    # Foundational
    "CLF-C02": "AWS Certified Cloud Practitioner",
    "AIF-C01": "AWS Certified AI Practitioner",
    # Associate
    "SAA-C03": "AWS Certified Solutions Architect - Associate",
    "DVA-C02": "AWS Certified Developer - Associate",
    "SOA-C02": "AWS Certified SysOps Administrator - Associate",
    "SOA-C03": "AWS Certified CloudOps Engineer - Associate",
    "DEA-C01": "AWS Certified Data Engineer - Associate",
    "MLA-C01": "AWS Certified Machine Learning Engineer - Associate",
    # Professional
    "SAP-C02": "AWS Certified Solutions Architect - Professional",
    "DOP-C02": "AWS Certified DevOps Engineer - Professional",
    "AIP-C01": "AWS Certified Generative AI Developer - Professional",
    # Specialty
    "ANS-C01": "AWS Certified Advanced Networking - Specialty",
    "SCS-C03": "AWS Certified Security - Specialty",
    "MLS-C01": "AWS Certified Machine Learning - Specialty",
    "DBS-C01": "AWS Certified Database - Specialty",
    "DAS-C01": "AWS Certified Data Analytics - Specialty",
}


def lambda_handler(event, context):
    cert_code = event.get("cert_code", "SAA-C03")
    cert_name = CERT_NAMES.get(cert_code, cert_code)

    # Pick enough due topics to fill QUESTIONS_PER_EMAIL with QUESTIONS_PER_TOPIC each
    topics_needed = (QUESTIONS_PER_EMAIL + QUESTIONS_PER_TOPIC - 1) // QUESTIONS_PER_TOPIC
    topic_rows = get_due_topics(cert_code, topics_needed)
    if not topic_rows:
        print(f"No due topics for {cert_code}, skipping this run")
        return {"status": "no_topics"}

    quizzes = []
    for row in topic_rows:
        if len(quizzes) >= QUESTIONS_PER_EMAIL:
            break
        for _ in range(QUESTIONS_PER_TOPIC):
            if len(quizzes) >= QUESTIONS_PER_EMAIL:
                break
            try:
                question = generate_question(cert_name, row["domain"], row["topic"])
            except Exception as e:
                print(f"Failed to generate question for topic '{row['topic']}': {e}")
                continue
            quiz_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            save_pending_quiz(quiz_id, cert_code, row["topic"], question)
            quizzes.append({"quiz_id": quiz_id, "topic": row["topic"], "question": question})

    if not quizzes:
        return {"status": "all_failed"}

    send_email(cert_name, quizzes)

    return {
        "status": "sent",
        "count": len(quizzes),
        "topics": list({q["topic"] for q in quizzes}),
    }


def get_due_topics(cert_code, limit=5):
    table = dynamodb.Table(TOPICS_TABLE)
    today = datetime.now(timezone.utc).date().isoformat()

    resp = table.query(KeyConditionExpression=Key("cert_code").eq(cert_code))
    items = resp.get("Items", [])
    due = [i for i in items if i.get("next_due", today) <= today]
    due.sort(key=lambda i: i.get("next_due", today))
    return due[:limit]


def generate_question(cert_name, domain, topic):
    prompt = f"""You are writing one practice question for the {cert_name} exam.
Domain: {domain}
Topic: {topic}

Return only JSON in this exact format, no other text:
{{
  "question": "...",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct": "A",
  "explanation": "one or two sentences on why the answer is correct"
}}
Make the question scenario based where it fits the topic, and make sure exactly one option is correct."""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = bedrock.invoke_model(modelId=BEDROCK_MODEL_ID, body=json.dumps(body))
    payload = json.loads(response["body"].read())
    text = payload["content"][0]["text"].strip()
    text = text.strip("`").replace("json\n", "", 1).strip()
    return json.loads(text)


def save_pending_quiz(quiz_id, cert_code, topic, question):
    table = dynamodb.Table(PENDING_TABLE)
    ttl = int(time.time()) + 60 * 60 * 48
    table.put_item(Item={
        "quiz_id": quiz_id,
        "cert_code": cert_code,
        "topic": topic,
        "correct": question["correct"],
        "explanation": question["explanation"],
        "ttl": ttl,
    })


def send_email(cert_name, quizzes):
    sections = []
    for idx, q in enumerate(quizzes, start=1):
        options_html = "".join(
            f'<p><a href="{API_BASE_URL}/answer?quiz_id={q["quiz_id"]}&choice={k}">{k}. {v}</a></p>'
            for k, v in q["question"]["options"].items()
        )
        sections.append(f"""
        <hr>
        <h3>Question {idx}: {q['topic']}</h3>
        <p>{q['question']['question']}</p>
        {options_html}
        """)

    html_body = f"""
    <h2>{cert_name} - daily questions ({len(quizzes)})</h2>
    {''.join(sections)}
    <hr>
    <p style="color:#888;font-size:small">Click an option to submit your answer and see the explanation.</p>
    """
    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [RECIPIENT_EMAIL]},
        Message={
            "Subject": {"Data": f"Daily {cert_name} questions: {len(quizzes)} topics"},
            "Body": {"Html": {"Data": html_body}},
        },
    )
