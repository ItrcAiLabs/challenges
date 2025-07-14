import os
import json
import logging
import random
import string
import uuid
from django.conf import settings
from django.core.files.base import ContentFile

from base.utils import (
    get_model_object,
    send_email,
)

from .models import (
    Challenge,
    ChallengePhase,
    Leaderboard,
    DatasetSplit,
    ChallengePhaseSplit,
    ParticipantTeam,
)

logger = logging.getLogger(__name__)

get_challenge_model = get_model_object(Challenge)

get_challenge_phase_model = get_model_object(ChallengePhase)

get_leaderboard_model = get_model_object(Leaderboard)

get_dataset_split_model = get_model_object(DatasetSplit)

get_challenge_phase_split_model = get_model_object(ChallengePhaseSplit)

get_participant_model = get_model_object(ParticipantTeam)


def get_missing_keys_from_dict(dictionary, keys):
    """
    Function to get a list of missing keys from a python dict.

    Parameters:
    dict: keys-> 'dictionary': A python dictionary.
                 'keys': List of keys to check for in the dictionary.

    Returns:
    list: A list of keys missing from the dictionary object.
    """
    missing_keys = []
    for key in keys:
        if key not in dictionary.keys():
            missing_keys.append(key)
    return missing_keys


def get_file_content(file_path, mode):
    if os.path.isfile(file_path):
        with open(file_path, mode) as file_content:
            return file_content.read()


def read_file_data_as_content_file(file_path, mode, name):
    content_file = ContentFile(get_file_content(file_path, mode), name)
    return content_file



def is_user_in_allowed_email_domains(email, challenge_pk):
    challenge = get_challenge_model(challenge_pk)
    for domain in challenge.allowed_email_domains:
        if domain.lower() in email.lower():
            return True
    return False


def is_user_in_blocked_email_domains(email, challenge_pk):
    challenge = get_challenge_model(challenge_pk)
    for domain in challenge.blocked_email_domains:
        domain = "@" + domain
        if domain.lower() in email.lower():
            return True
    return False


def get_unique_alpha_numeric_key(length):
    """
    Returns unique alpha numeric key of length
    Arguments:
        length {int} -- length of unique key to generate
    Returns:
        key {string} -- unique alpha numeric key of length
    """
    return "".join(
        [
            random.choice(string.ascii_letters + string.digits)
            for i in range(length)
        ]
    )


def get_challenge_template_data(challenge):
    """
    Returns a dict for sendgrid email template data
    Arguments:
        challenge {Class Object} -- Challenge model object
    Returns:
        template_data {dict} -- a dict for sendgrid email template data
    """
    challenge_url = "{}/web/challenges/challenge-page/{}".format(
        settings.EVALAI_API_SERVER, challenge.id
    )
    challenge_manage_url = "{}/web/challenges/challenge-page/{}/manage".format(
        settings.EVALAI_API_SERVER, challenge.id
    )
    template_data = {
        "CHALLENGE_NAME": challenge.title,
        "CHALLENGE_URL": challenge_url,
        "CHALLENGE_MANAGE_URL": challenge_manage_url,
    }
    return template_data


def send_emails(emails, template_id, template_data):
    """
    Sends email to list of users using provided template
    Arguments:
        emails {list} -- recepient email ids
        template_id {string} -- sendgrid template id
        template_data {dict} -- sendgrid email template data
    """
    for email in emails:
        send_email(
            sender=settings.CLOUDCV_TEAM_EMAIL,
            recipient=email,
            template_id=template_id,
            template_data=template_data,
        )


def parse_submission_meta_attributes(submission):
    """
    Extracts submission attributes into Dict
    Arguments:
        submission {dict} -- Serialized submission object
    Returns:
        submission_meta_attributes {dict} -- a dict of submission meta attributes
    """
    submission_meta_attributes = {}
    if submission["submission_metadata"] is None:
        return {}
    for meta_attribute in submission["submission_metadata"]:
        if meta_attribute["type"] == "checkbox":
            submission_meta_attributes[
                meta_attribute["name"]
            ] = meta_attribute.get("values")
        else:
            submission_meta_attributes[
                meta_attribute["name"]
            ] = meta_attribute.get("value")
    return submission_meta_attributes
