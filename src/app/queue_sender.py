"""Module to publish processed analysis data to RabbitMQ or AWS SQS."""

import json
import os

import boto3
import pika
from botocore.exceptions import BotoCoreError, NoCredentialsError

from app.logger import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Get queue type from environment
QUEUE_TYPE = os.getenv("QUEUE_TYPE", "rabbitmq").lower()

# RabbitMQ config
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "stock_analysis")
RABBITMQ_ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY", "volatility")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

# SQS config
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
SQS_REGION = os.getenv("SQS_REGION", "us-east-1")

# Initialize SQS client if needed
sqs_client = None
if QUEUE_TYPE == "sqs":
    try:
        sqs_client = boto3.client("sqs", region_name=SQS_REGION)
        logger.info(f"SQS client initialized for region {SQS_REGION}")
    except (BotoCoreError, NoCredentialsError) as e:
        logger.error("Failed to initialize SQS client: %s", e)
        sqs_client = None


def publish_to_queue(payload: list[dict[str, Any]]) -> None:
    """Publishes the processed stock analysis results to RabbitMQ or SQS.

    Args:
    ----
        payload (list[dict[str, Any]]): A list of dictionaries representing processed results.
            Each dictionary should contain the following keys:
                'symbol': str, the stock symbol.
                'analysis_type': str, the type of analysis performed.
                'analysis_data': dict[str, Any], the results of the analysis.

    Returns:
    -------
        None

    """
    for message in payload:
        if QUEUE_TYPE == "rabbitmq":
            _send_to_rabbitmq(message)
        elif QUEUE_TYPE == "sqs":
            _send_to_sqs(message)
        else:
            logger.error("Invalid QUEUE_TYPE specified. Use 'rabbitmq' or 'sqs'.")


def _send_to_rabbitmq(data: dict[str, Any]) -> None:
    """Helper to send a message to RabbitMQ.

    Args:
    ----
        data (dict[str, Any]): The message data to be sent, serialized as JSON.

    Returns:
    -------
        None

    """
    try:
        # Establish a connection to RabbitMQ
        connection: pika.BlockingConnection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, virtual_host=RABBITMQ_VHOST)
        )
        channel = connection.channel()

        # Publish the message to the specified exchange and routing key
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            body=json.dumps(data),
        )

        # Close the connection after publishing the message
        connection.close()
        logger.info("Published message to RabbitMQ")
    except Exception as e:
        logger.error("Failed to publish message to RabbitMQ: %s", e)


def _send_to_sqs(data: dict[str, Any]) -> None:
    """Helper to send a message to AWS SQS.

    If `sqs_client` is not initialized or `SQS_QUEUE_URL` is not set, a log
    message is emitted and the function returns without attempting to send the
    message.

    Args:
    ----
        data (dict[str, Any]): The message data to be sent, serialized as JSON.

    Returns:
    -------
        None

    """
    if not sqs_client or not SQS_QUEUE_URL:
        logger.error("SQS client is not initialized or missing SQS_QUEUE_URL")
        return

    try:
        # Send the message to the specified SQS queue
        response: dict[str, str] = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(data),
        )
        logger.info("Published message to SQS, MessageId: %s", response["MessageId"])
    except Exception as e:
        logger.error("Failed to publish message to SQS: %s", e)
