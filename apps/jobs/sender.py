from __future__ import absolute_import
from confluent_kafka import Producer
import json
import logging
import os

from django.conf import settings

from base.utils import send_slack_notification
from challenges.models import Challenge
from .utils import get_submission_model
from monitoring.statsd.metrics import NUM_SUBMISSIONS_IN_QUEUE, increment_statsd_counter

logger = logging.getLogger(__name__)




def publish_submission_message(message):
    """
    Args:
        message: A Dict with following keys
            - "challenge_pk": int
            - "phase_pk": int
            - "submission_pk": int
            - "submitted_image_uri": str, (only available when the challenge is a code upload challenge)
            - "is_static_dataset_code_upload_submission": bool

    Returns:
        Returns SQS response
    """

    try:
        challenge = Challenge.objects.get(pk=message["challenge_pk"])
    except Challenge.DoesNotExist:
        logger.exception(
            "Challenge does not exist for the given id {}".format(
                message["challenge_pk"]
            )
        )
        return
    queue_name = 'evalai_submission_queue'
    broker = "localhost:9092"
    producer = None
    response = json.dumps(message)
    print(response)
    slack_url = challenge.slack_webhook_url
    is_remote = challenge.remote_evaluation
    producer = Producer({
        'bootstrap.servers': broker,
        'socket.timeout.ms': 100,
        'api.version.request': 'false',
        'broker.version.fallback': '0.9.0',
    }
    )

    def delivery_report(err, message):
        """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
        if err is not None:
            print('Message delivery failed: {}'.format(err))
        else:
            print('Message delivered to {} [{}]'.format(
                message.topic(), message.partition()))

    producer.produce(
        queue_name,
        response,
        callback=lambda err, original_message=response: delivery_report(err, original_message
                                                                        ),
    )
    producer.flush()
    # increase counter for submission pushed into queue
    submission_metric_tags = [
        "queue_name:%s" % queue_name,
        "is_remote:%d" % int(is_remote)
    ]
    increment_statsd_counter(NUM_SUBMISSIONS_IN_QUEUE, submission_metric_tags, 1)

    # send slack notification
    if slack_url:
        challenge_name = challenge.title
        submission = get_submission_model(message["submission_pk"])
        participant_team_name = submission.participant_team.team_name
        phase_name = submission.challenge_phase.name
        message = {
            "text": "A *new submission* has been uploaded to {}".format(
                challenge_name
            ),
            "fields": [
                {
                    "title": "Challenge Phase",
                    "value": phase_name,
                    "short": True,
                },
                {
                    "title": "Participant Team Name",
                    "value": participant_team_name,
                    "short": True,
                },
                {
                    "title": "Submission Id",
                    "value": message["submission_pk"],
                    "short": True,
                },
            ],
        }
        send_slack_notification(slack_url, message)
    return response
