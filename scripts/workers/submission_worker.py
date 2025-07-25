from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from time import sleep
import contextlib
import django
import importlib
import json
import logging
import os
import requests
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import yaml
import zipfile
from confluent_kafka import Consumer

from os.path import join

from django.core.files.base import ContentFile
from django.utils import timezone
# from monitoring.statsd.metrics import NUM_PROCESSED_SUBMISSIONS, increment_statsd_counter

# all challenge and submission will be stored in temp directory
BASE_TEMP_DIR = tempfile.mkdtemp()
COMPUTE_DIRECTORY_PATH = join(BASE_TEMP_DIR, "compute")

formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', "settings.prod")
django.setup()

# Load django app settings
from django.conf import settings  # noqa
from challenges.models import (  # noqa:E402
    Challenge,
    ChallengePhase,
    ChallengePhaseSplit,
    LeaderboardData,
)

from jobs.models import Submission  # noqa:E402
from jobs.serializers import SubmissionSerializer  # noqa:E402

LIMIT_CONCURRENT_SUBMISSION_PROCESSING = os.environ.get(
    "LIMIT_CONCURRENT_SUBMISSION_PROCESSING", "False"
)
DJANGO_SETTINGS_MODULE = os.environ.get(
    "DJANGO_SETTINGS_MODULE", "settings.prod"
)

CHALLENGE_DATA_BASE_DIR = join(COMPUTE_DIRECTORY_PATH, "challenge_data")
SUBMISSION_DATA_BASE_DIR = join(COMPUTE_DIRECTORY_PATH, "submission_files")
CHALLENGE_DATA_DIR = join(CHALLENGE_DATA_BASE_DIR, "challenge_{challenge_id}")
PHASE_DATA_BASE_DIR = join(CHALLENGE_DATA_DIR, "phase_data")
PHASE_DATA_DIR = join(PHASE_DATA_BASE_DIR, "phase_{phase_id}")
PHASE_ANNOTATION_FILE_PATH = join(PHASE_DATA_DIR, "{annotation_file}")
SUBMISSION_DATA_DIR = join(
    SUBMISSION_DATA_BASE_DIR, "submission_{submission_id}"
)
SUBMISSION_INPUT_FILE_PATH = join(SUBMISSION_DATA_DIR, "{input_file}")
CHALLENGE_IMPORT_STRING = "challenge_data.challenge_{challenge_id}"
EVALUATION_SCRIPTS = {}

# map of challenge id : phase id : phase annotation file name
# Use: On arrival of submission message, lookup here to fetch phase file name
# this saves db query just to fetch phase annotation file name
PHASE_ANNOTATION_FILE_NAME_MAP = {}
WORKER_LOGS_PREFIX = "WORKER_LOG"
SUBMISSION_LOGS_PREFIX = "SUBMISSION_LOG"

django.db.close_old_connections()


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True


class ExecutionTimeLimitExceeded(Exception):
    pass


class MultiOut(object):
    def __init__(self, *args):
        self.handles = args

    def write(self, s):
        for f in self.handles:
            f.write(s)

    def flush(self):
        for f in self.handles:
            f.flush()


@contextlib.contextmanager
def stdout_redirect(where):
    sys.stdout = where
    try:
        yield where
    finally:
        sys.stdout = sys.__stdout__


@contextlib.contextmanager
def stderr_redirect(where):
    sys.stderr = where
    try:
        yield where
    finally:
        sys.stderr = sys.__stderr__


def alarm_handler(signum, frame):
    raise ExecutionTimeLimitExceeded


def download_and_extract_file(url, download_location):
    """
    * Function to extract download a file.
    * `download_location` should include name of file as well.
    """
    import shutil

    if os.path.isfile(url):
        shutil.copyfile(url, download_location)


def extract_zip_file(download_location, extract_location):
    """
    Helper function to extract zip file
    Params:
        * `download_location`: Location of zip file
        * `extract_location`: Location of directory for extracted file
    """
    zip_ref = zipfile.ZipFile(download_location, "r")
    zip_ref.extractall(extract_location)
    zip_ref.close()


def delete_zip_file(download_location):
    """
    Helper function to remove zip file from location `download_location`
    Params:
        * `download_location`: Location of file to be removed.
    """
    try:
        os.remove(download_location)
    except Exception as e:
        logger.error(
            "{} Failed to remove zip file {}, error {}".format(
                WORKER_LOGS_PREFIX, download_location, e
            )
        )
        traceback.print_exc()


def delete_submission_data_directory(location):
    """
    Helper function to delete submission data from location `location`

    Arguments:
        location {[string]} -- Location of directory to be removed.
    """
    try:
        shutil.rmtree(location)
    except Exception as e:
        logger.exception(
            "{} Failed to delete submission data directory {}, error {}".format(
                WORKER_LOGS_PREFIX, location, e
            )
        )


def download_and_extract_zip_file(url, download_location, extract_location):
    """
    * Function to extract download a zip file, extract it and then removes the zip file.
    * `download_location` should include name of file as well.
    """
    # try:
    #     response = requests.get(url, stream=True)
    # except Exception as e:
    #     logger.error(
    #         "{} Failed to fetch file from {}, error {}".format(
    #             WORKER_LOGS_PREFIX, url, e
    #         )
    #     )
    #     response = None

    import shutil
    import os.path

    if os.path.isfile(url):
        shutil.copyfile(url, download_location)
        extract_zip_file(download_location, extract_location)
        # delete zip file
        delete_zip_file(download_location)


def create_dir(directory):
    """
    Creates a directory if it does not exists
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def create_dir_as_python_package(directory):
    """
    Create a directory and then makes it a python
    package by creating `__init__.py` file.
    """
    create_dir(directory)
    init_file_path = join(directory, "__init__.py")
    with open(init_file_path, "w") as init_file:  # noqa
        # to create empty file
        pass



def extract_challenge_data(challenge, phases):
    """
    * Expects a challenge object and an array of phase object
    * Extracts `evaluation_script` for challenge and `annotation_file` for each phase

    """

    challenge_data_directory = CHALLENGE_DATA_DIR.format(
        challenge_id=challenge.id
    )
    # create challenge directory as package
    create_dir_as_python_package(challenge_data_directory)

    evaluation_script_url = challenge.evaluation_script.path

    # set entry in map
    PHASE_ANNOTATION_FILE_NAME_MAP[challenge.id] = {}

    challenge_zip_file = join(
        challenge_data_directory, "challenge_{}.zip".format(challenge.id)
    )
    download_and_extract_zip_file(
        evaluation_script_url, challenge_zip_file, challenge_data_directory
    )

    try:
        requirements_location = join(challenge_data_directory, "requirements.txt")
        if os.path.isfile(requirements_location):
            subprocess.check_output([sys.executable, "-m", "pip", "install", "-r", requirements_location])
        else:
            logger.info("No custom requirements for challenge {}".format(challenge.id))
    except Exception as e:
        logger.error(e)

    phase_data_base_directory = PHASE_DATA_BASE_DIR.format(
        challenge_id=challenge.id
    )
    create_dir(phase_data_base_directory)

    for phase in phases:
        try:
            phase_data_directory = PHASE_DATA_DIR.format(
                challenge_id=challenge.id, phase_id=phase.id
            )
            # create phase directory
            create_dir(phase_data_directory)
            annotation_file_url = phase.test_annotation.path
            annotation_file_name = os.path.basename(phase.test_annotation.name)
            PHASE_ANNOTATION_FILE_NAME_MAP[challenge.id][
                phase.id
            ] = annotation_file_name
            annotation_file_path = PHASE_ANNOTATION_FILE_PATH.format(
                challenge_id=challenge.id,
                phase_id=phase.id,
                annotation_file=annotation_file_name,
            )
            download_and_extract_file(annotation_file_url, annotation_file_path)
        except Exception:
            pass

    try:
        # import the challenge after everything is finished
        importlib.invalidate_caches()
        challenge_module = importlib.import_module(
            CHALLENGE_IMPORT_STRING.format(challenge_id=challenge.id)
        )
        EVALUATION_SCRIPTS[challenge.id] = challenge_module
    except Exception:
        logger.exception(
            "{} Exception raised while creating Python module for challenge_id: {}".format(
                WORKER_LOGS_PREFIX, challenge.id
            )
        )
        raise


def load_challenge(challenge):
    """
    Creates python package for a challenge and extracts relevant data
    """
    # make sure that the challenge base directory exists
    create_dir_as_python_package(CHALLENGE_DATA_BASE_DIR)
    phases = challenge.challengephase_set.all()
    extract_challenge_data(challenge, phases)


def extract_submission_data(submission_id):
    """
    * Expects submission id and extracts input file for it.
    """
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        logger.critical(
            "{} Submission {} does not exist".format(
                SUBMISSION_LOGS_PREFIX, submission_id
            )
        )
        traceback.print_exc()
        # return from here so that the message can be acked
        # This also indicates that we don't want to take action
        # for message corresponding to which submission entry
        # does not exist
        return None
    # Ignore submissions with status cancelled
    if submission.status == Submission.CANCELLED:
        logger.info(
            "{} Submission {} was cancelled by the user".format(
                SUBMISSION_LOGS_PREFIX, submission_id
            )
        )
        return None

    if submission.challenge_phase.challenge.is_static_dataset_code_upload:
        input_file = submission.submission_input_file
    else:
        input_file = submission.input_file
    submission_input_file = input_file.path

    submission_data_directory = SUBMISSION_DATA_DIR.format(
        submission_id=submission.id
    )
    submission_input_file_name = os.path.basename(input_file.name)
    submission_input_file_path = SUBMISSION_INPUT_FILE_PATH.format(
        submission_id=submission.id, input_file=submission_input_file_name
    )
    # create submission directory
    create_dir_as_python_package(submission_data_directory)

    download_and_extract_file(
        submission_input_file, submission_input_file_path
    )

    return submission


def run_submission(
        challenge_id, challenge_phase, submission, user_annotation_file_path
):
    """
    * receives a challenge id, phase id and user annotation file path
    * checks whether the corresponding evaluation script for the challenge exists or not
    * checks the above for annotation file
    * calls evaluation script via subprocess passing annotation file and user_annotation_file_path as argument
    """

    # Use the submission serializer to send relevant data to evaluation script
    # so that challenge hosts can use data for webhooks or any other service.
    submission_serializer = SubmissionSerializer(submission)

    submission_output = None
    phase_id = challenge_phase.id
    annotation_file_name = PHASE_ANNOTATION_FILE_NAME_MAP.get(
        challenge_id
    ).get(phase_id)
    annotation_file_path = PHASE_ANNOTATION_FILE_PATH.format(
        challenge_id=challenge_id,
        phase_id=phase_id,
        annotation_file=annotation_file_name,
    )
    submission_data_dir = SUBMISSION_DATA_DIR.format(
        submission_id=submission.id
    )

    submission.status = Submission.RUNNING
    submission.started_at = timezone.now()
    submission.save()

    # create a temporary run directory under submission directory, so that
    # main directory does not gets polluted
    temp_run_dir = join(submission_data_dir, "run")
    create_dir(temp_run_dir)

    stdout_file = join(temp_run_dir, "temp_stdout.txt")
    stderr_file = join(temp_run_dir, "temp_stderr.txt")

    stdout = open(stdout_file, "a+")
    stderr = open(stderr_file, "a+")

    remote_evaluation = submission.challenge_phase.challenge.remote_evaluation

    if remote_evaluation:
        try:
            logger.info(
                "{} Sending submission {} for remote evaluation".format(
                    SUBMISSION_LOGS_PREFIX, submission.id
                )
            )
            with stdout_redirect(
                    MultiOut(stdout, sys.__stdout__)
            ) as new_stdout, stderr_redirect(  # noqa
                MultiOut(stderr, sys.__stderr__)
            ) as new_stderr:  # noqa
                submission_output = EVALUATION_SCRIPTS[challenge_id].evaluate(
                    annotation_file_path,
                    user_annotation_file_path,
                    challenge_phase.codename,
                    submission_metadata=submission_serializer.data,
                )
                return
        except Exception:
            stderr.write(traceback.format_exc())
            stderr.close()
            stdout.close()
            submission.status = Submission.FAILED
            submission.completed_at = timezone.now()
            submission.save()
            with open(stdout_file, "r") as stdout:
                stdout_content = stdout.read()
                submission.stdout_file.save(
                    "stdout.txt", ContentFile(stdout_content)
                )
            with open(stderr_file, "r") as stderr:
                stderr_content = stderr.read()
                submission.stderr_file.save(
                    "stderr.txt", ContentFile(stderr_content)
                )

            # delete the complete temp run directory
            shutil.rmtree(temp_run_dir)
            return

    # call `main` from globals and set `status` to running and hence `started_at`
    try:
        successful_submission_flag = True
        with stdout_redirect(
                MultiOut(stdout, sys.__stdout__)
        ) as new_stdout, stderr_redirect(  # noqa
            MultiOut(stderr, sys.__stderr__)
        ) as new_stderr:  # noqa
            submission_output = EVALUATION_SCRIPTS[challenge_id].evaluate(
                annotation_file_path,
                user_annotation_file_path,
                challenge_phase.codename,
                submission_metadata=submission_serializer.data,
            )
        """
        A submission will be marked successful only if it is of the format
            {
               "result":[
                  {
                     "split_codename_1":{
                        "key1":30,
                        "key2":50,
                     }
                  },
                  {
                     "split_codename_2":{
                        "key1":90,
                        "key2":10,
                     }
                  },
                  {
                     "split_codename_3":{
                        "key1":100,
                        "key2":45,
                     }
                  }
               ],
               "submission_metadata": {'foo': 'bar'},
               "submission_result": ['foo', 'bar'],
            }
        """

        error_bars_dict = dict()
        if "error" in submission_output:
            for split_error in submission_output["error"]:
                split_code_name = list(split_error.keys())[0]
                error_bars_dict[split_code_name] = split_error[split_code_name]

        if "result" in submission_output:

            leaderboard_data_list = []
            for split_result in submission_output["result"]:
                # get split_code_name that is the key of the result
                split_code_name = list(split_result.keys())[0]

                # Check if the challenge_phase_split exists for the challenge_phaseand dataset_split
                try:
                    logger.info(challenge_phase)
                    logger.info(split_code_name)
                    challenge_phase_split = ChallengePhaseSplit.objects.get(
                        challenge_phase=challenge_phase,
                        dataset_split__codename=split_code_name,
                    )
                except Exception:
                    stderr.write(
                        "ORGINIAL EXCEPTION: No such relations between Challenge Phase and DatasetSplit"
                        " specified by Challenge Host {}, {}, {} \n".format("test", challenge_phase, split_code_name)
                    )
                    stderr.write(traceback.format_exc())
                    successful_submission_flag = False
                    break

                # Check if the dataset_split exists for the codename in the result
                try:
                    dataset_split = challenge_phase_split.dataset_split
                except Exception:
                    stderr.write(
                        "ORGINIAL EXCEPTION: The codename specified by your Challenge Host doesn't match"
                        " with that in the evaluation Script.\n"
                    )
                    stderr.write(traceback.format_exc())
                    successful_submission_flag = False
                    break

                leaderboard_data = LeaderboardData()
                leaderboard_data.challenge_phase_split = challenge_phase_split
                leaderboard_data.submission = submission
                leaderboard_data.leaderboard = (
                    challenge_phase_split.leaderboard
                )
                leaderboard_data.result = split_result.get(
                    dataset_split.codename
                )

                if "error" in submission_output:
                    leaderboard_data.error = error_bars_dict.get(
                        dataset_split.codename
                    )

                leaderboard_data_list.append(leaderboard_data)

            if successful_submission_flag:
                LeaderboardData.objects.bulk_create(leaderboard_data_list)

        # Once the submission_output is processed, then save the submission object with appropriate status
        else:
            successful_submission_flag = False

    except Exception:
        stderr.write(traceback.format_exc())
        successful_submission_flag = False
        # Set submission_output to None to handle case when evaluation script throws exception
        # In case of exception from evaluation script submission_output is assigned exception object
        submission_output = None

    submission_status = (
        Submission.FINISHED
        if successful_submission_flag
        else Submission.FAILED
    )
    submission.status = submission_status
    submission.completed_at = timezone.now()
    submission.save()

    # after the execution is finished, set `status` to finished and hence `completed_at`
    if submission_output:
        output = {}
        output["result"] = submission_output.get("result", "")
        submission.output = output

        # Save submission_result_file
        submission_result = submission_output.get("submission_result", "")
        submission_result = json.dumps(submission_result)
        submission.submission_result_file.save(
            "submission_result.json", ContentFile(submission_result)
        )

        # Save submission_metadata_file
        submission_metadata = submission_output.get("submission_metadata", "")
        submission.submission_metadata_file.save(
            "submission_metadata.json", ContentFile(submission_metadata)
        )
        submission.save()

    stderr.close()
    stdout.close()
    stderr_content = open(stderr_file, "r").read()
    stdout_content = open(stdout_file, "r").read()

    # TODO :: see if two updates can be combine into a single update.
    with open(stdout_file, "r") as stdout:
        stdout_content = stdout.read()
        submission.stdout_file.save("stdout.txt", ContentFile(stdout_content))
    if submission_status is Submission.FAILED:
        with open(stderr_file, "r") as stderr:
            stderr_content = stderr.read().encode("utf-8")
            submission.stderr_file.save(
                "stderr.txt", ContentFile(stderr_content)
            )

    # delete the complete temp run directory
    shutil.rmtree(temp_run_dir)


def process_submission_message(message):
    """
    Extracts the submission related metadata from the message
    and send the submission object for evaluation
    """
    challenge_id = message.get("challenge_pk")
    phase_id = message.get("phase_pk")
    submission_id = message.get("submission_pk")
    submission_instance = extract_submission_data(submission_id)

    # so that the further execution does not happen
    if not submission_instance:
        return

    try:
        challenge_phase = ChallengePhase.objects.get(id=phase_id)
    except ChallengePhase.DoesNotExist:
        logger.exception(
            "{} Challenge Phase {} does not exist".format(
                WORKER_LOGS_PREFIX, phase_id
            )
        )
        raise

    if (
            submission_instance.challenge_phase.challenge.is_static_dataset_code_upload
    ):
        input_file_name = submission_instance.submission_input_file.name
    else:
        input_file_name = submission_instance.input_file.name
    user_annotation_file_path = join(
        SUBMISSION_DATA_DIR.format(submission_id=submission_id),
        os.path.basename(input_file_name),
    )
    run_submission(
        challenge_id,
        challenge_phase,
        submission_instance,
        user_annotation_file_path,
    )
    # Delete submission data after processing submission
    delete_submission_data_directory(
        SUBMISSION_DATA_DIR.format(submission_id=submission_id)
    )


def process_add_challenge_message(message):
    challenge_id = message.get("challenge_id")

    try:
        challenge = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        logger.exception(
            "{} Challenge {} does not exist".format(
                WORKER_LOGS_PREFIX, challenge_id
            )
        )

    phases = challenge.challengephase_set.all()
    extract_challenge_data(challenge, phases)


def process_submission_callback(body):
    try:
        logger.info(
            "{} [x] Received submission message {}".format(
                SUBMISSION_LOGS_PREFIX, body
            )
        )
        body = yaml.safe_load(body)
        body = dict((k, int(v)) for k, v in body.items())
        process_submission_message(body)
    except Exception as e:
        logger.exception(
            "{} Exception while receiving message from submission queue with error {}".format(
                SUBMISSION_LOGS_PREFIX, e
            )
        )


def load_challenge_and_return_max_submissions(q_params):
    try:
        challenge = Challenge.objects.get(**q_params)
    except Challenge.DoesNotExist:
        logger.exception(
            "{} Challenge with pk {} doesn't exist".format(
                WORKER_LOGS_PREFIX, q_params["pk"]
            )
        )
        raise
    load_challenge(challenge)
    maximum_concurrent_submissions = (
        challenge.max_concurrent_submission_evaluation
    )
    return maximum_concurrent_submissions, challenge


def increment_and_push_metrics_to_statsd(queue_name, is_remote):
    try:
        submission_metric_tags = [
            "queue_name:%s" % queue_name,
            "is_remote:%d" % is_remote,
        ]
        # increment_statsd_counter(NUM_PROCESSED_SUBMISSIONS, submission_metric_tags, 1)
    except Exception as e:
        logger.exception(
            "{} Exception when pushing metrics to statsd: {}".format(
                SUBMISSION_LOGS_PREFIX, e
            )
        )


def main():
    killer = GracefulKiller()
    logger.info(
        "{} Using {} as temp directory to store data".format(
            WORKER_LOGS_PREFIX, BASE_TEMP_DIR
        )
    )
    create_dir_as_python_package(COMPUTE_DIRECTORY_PATH)
    sys.path.append(COMPUTE_DIRECTORY_PATH)

    q_params = {}
    q_params["end_date__gt"] = timezone.now()

    challenge_pk = os.environ.get("CHALLENGE_PK")
    if challenge_pk:
        q_params["pk"] = challenge_pk


    # create submission base data directory
    create_dir_as_python_package(SUBMISSION_DATA_BASE_DIR)
    queue_name = 'evalai_submission_queue'
    broker = "localhost:9092"
    group_id = "consumer-1"
    consumer_config = {
        'bootstrap.servers': broker,
        'group.id': group_id,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': 'false',
        'max.poll.interval.ms': '86400000'
    }

    consumer = Consumer(consumer_config)
    consumer.subscribe([queue_name])
    while True:
        message = (consumer.poll(0))

        if message is None:
            sleep(5)
            print('...')
            continue
        # Check if the message has no value or is empty
        message_value = message.value()
        if message_value is None or message_value == '':
            print('Empty message received, skipping...')
            continue

        try:
            # Attempt to parse the message as JSON
            message_data = json.loads(message_value)

            # Check if the specific key exists and if so, continue
            if message_data.get("is_static_dataset_code_upload_submission"):
                continue
        except json.JSONDecodeError as e:
            # Handle the case where the message is not valid JSON
            print(f"JSONDecodeError: Failed to parse message. Error: {e}")
            print(f"Message content: {message_value}")
            continue
        #if json.loads(message.value()).get(
        #        "is_static_dataset_code_upload_submission"
        #):
        #    continue

        q_params["end_date__gt"] = timezone.now()
        challenge_pk = json.loads(message.value()).get("challenge_pk")
        q_params["pk"] = challenge_pk
        (
            maximum_concurrent_submissions,
            challenge,
        ) = load_challenge_and_return_max_submissions(q_params)
        is_remote = int(challenge.remote_evaluation)

        current_running_submissions_count = Submission.objects.filter(
            challenge_phase__challenge=challenge.id, status="running"
        ).count()
        if (
                current_running_submissions_count
                == maximum_concurrent_submissions
        ):
            pass
        else:
            logger.info(
                "{} Processing message body: {}".format(
                    WORKER_LOGS_PREFIX, message.value()
                )
            )
            process_submission_callback(message.value())
            # Let the queue know that the message is processed
            # message.delete()
            increment_and_push_metrics_to_statsd(queue_name, is_remote)
        if killer.kill_now:
            break
    time.sleep(0.1)


if __name__ == "__main__":
    main()
    logger.info("{} Quitting Submission Worker.".format(WORKER_LOGS_PREFIX))
