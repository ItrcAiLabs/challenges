from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core import serializers
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.db.models import signals

from base.models import TimeStampedModel, model_field_name
from base.utils import RandomFileName, get_slug, is_model_field_changed


from participants.models import ParticipantTeam
from hosts.models import ChallengeHost


@receiver(pre_save, sender="challenges.Challenge")
def save_challenge_slug(sender, instance, **kwargs):
    title = get_slug(instance.title)
    instance.slug = "{}-{}".format(title, instance.pk)


def get_default_eval_metric():
    return ["Accuracy"]


class Challenge(TimeStampedModel):

    """Model representing a hosted Challenge"""

    def __init__(self, *args, **kwargs):
        super(Challenge, self).__init__(*args, **kwargs)
        self._original_evaluation_script = self.evaluation_script
        self._original_approved_by_admin = self.approved_by_admin

    title = models.CharField(max_length=100, db_index=True)
    short_description = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    terms_and_conditions = models.TextField(null=True, blank=True)
    submission_guidelines = models.TextField(null=True, blank=True)
    evaluation_details = models.TextField(null=True, blank=True)
    image = models.ImageField(
        upload_to=RandomFileName("logos"),
        null=True,
        blank=True,
        verbose_name="Logo",
    )
    start_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Start Date (UTC)", db_index=True
    )
    end_date = models.DateTimeField(
        null=True, blank=True, verbose_name="End Date (UTC)", db_index=True
    )
    creator = models.ForeignKey(
        "hosts.ChallengeHostTeam",
        related_name="challenge_creator",
        on_delete=models.CASCADE,
    )
    published = models.BooleanField(
        default=False, verbose_name="Publicly Available", db_index=True
    )
    submission_time_limit = models.PositiveIntegerField(default=86400)
    is_registration_open = models.BooleanField(default=True)
    enable_forum = models.BooleanField(default=True)
    forum_url = models.URLField(max_length=100, blank=True, null=True)
    leaderboard_description = models.TextField(null=True, blank=True)
    anonymous_leaderboard = models.BooleanField(default=False)
    participant_teams = models.ManyToManyField(ParticipantTeam, blank=True)
    is_disabled = models.BooleanField(default=False, db_index=True)
    evaluation_script = models.FileField(
        default=False, upload_to=RandomFileName("evaluation_scripts")
    )  # should be zip format
    approved_by_admin = models.BooleanField(
        default=False, verbose_name="Approved By Admin", db_index=True
    )
    featured = models.BooleanField(
        default=False, verbose_name="Featured", db_index=True
    )
    allowed_email_domains = ArrayField(
        models.CharField(max_length=50, blank=True), default=list, blank=True
    )
    blocked_email_domains = ArrayField(
        models.CharField(max_length=50, blank=True), default=list, blank=True
    )
    banned_email_ids = ArrayField(
        models.TextField(null=True, blank=True),
        default=list,
        blank=True,
        null=True,
    )
    remote_evaluation = models.BooleanField(
        default=False, verbose_name="Remote Evaluation", db_index=True
    )
    queue = models.CharField(
        max_length=200,
        default="",
        verbose_name="SQS queue name",
        db_index=True,
    )
    is_docker_based = models.BooleanField(
        default=False, verbose_name="Is Docker Based", db_index=True
    )
    is_static_dataset_code_upload = models.BooleanField(
        default=False,
        verbose_name="Is Static Dataset Code Upload Based",
        db_index=True,
    )
    slug = models.SlugField(max_length=200, null=True, unique=True)
    max_docker_image_size = models.BigIntegerField(
        default=42949672960, null=True, blank=True
    )  # Default is 40 GB
    max_concurrent_submission_evaluation = models.PositiveIntegerField(
        default=100000
    )

    use_host_credentials = models.BooleanField(default=False)
    cli_version = models.CharField(
        max_length=20, verbose_name="evalai-cli version", null=True, blank=True
    )
    # The number of active workers on Fargate of the challenge.
    workers = models.IntegerField(null=True, blank=True, default=None)
    # The task definition ARN for the challenge, used for updating and creating service.
    task_def_arn = models.CharField(
        null=True, blank=True, max_length=2048, default=""
    )
    slack_webhook_url = models.URLField(max_length=200, blank=True, null=True)
    # Identifier for the github repository of a challenge in format: account_name/repository_name
    github_repository = models.CharField(
        max_length=1000, null=True, blank=True, default=""
    )
    # The number of vCPU for a Fargate worker for the challenge. Default value is 0.25 vCPU.
    worker_cpu_cores = models.IntegerField(null=True, blank=True, default=512)
    # Memory size of a Fargate worker for the challenge. Default value is 0.5 GB memory.
    worker_memory = models.IntegerField(null=True, blank=True, default=1024)
    # Enable/Disable emails notifications for the challenge
    inform_hosts = models.BooleanField(default=True)
    # VPC and subnet CIDRs for code upload challenge
    vpc_cidr = models.CharField(
        null=True, blank=True, max_length=200, default=""
    )
    subnet_1_cidr = models.CharField(
        null=True, blank=True, max_length=200, default=""
    )
    subnet_2_cidr = models.CharField(
        null=True, blank=True, max_length=200, default=""
    )
    # Evaluation instance config for code upload challenge
    worker_instance_type = models.CharField(
        max_length=256, null=True, blank=True, default="g4dn.xlarge"
    )
    worker_ami_type = models.CharField(
        max_length=256, null=True, blank=True, default="AL2_x86_64_GPU"
    )
    worker_disk_size = models.IntegerField(null=True, blank=True, default=100)
    max_worker_instance = models.IntegerField(
        null=True, blank=True, default=10
    )
    min_worker_instance = models.IntegerField(null=True, blank=True, default=1)
    desired_worker_instance = models.IntegerField(
        null=True, blank=True, default=1
    )
    cpu_only_jobs = models.BooleanField(default=False)
    # The number of vCPU for a code upload submission kubernetes job. Default value is 2 vCPU.
    job_cpu_cores = models.CharField(
        max_length=256, null=True, blank=True, default="2000m"
    )
    job_memory = models.CharField(
        max_length=256, null=True, blank=True, default="8Gi"
    )

    class Meta:
        app_label = "challenges"
        db_table = "challenge"

    def __str__(self):
        """Returns the title of Challenge"""
        return self.title

    def get_image_url(self):
        """Returns the url of logo of Challenge"""
        if self.image:
            return self.image.url
        return None

    def get_evaluation_script_path(self):
        """Returns the path of evaluation script"""
        if self.evaluation_script:
            return self.evaluation_script.url
        return None

    def get_start_date(self):
        """Returns the start date of Challenge"""
        return self.start_date

    def get_end_date(self):
        """Returns the end date of Challenge"""
        return self.end_date

    @property
    def is_active(self):
        """Returns if the challenge is active or not"""
        if self.start_date < timezone.now() and self.end_date > timezone.now():
            return True
        return False

class DatasetSplit(TimeStampedModel):
    name = models.CharField(max_length=100)
    codename = models.CharField(max_length=100)
    # Id in the challenge config file. Needed to map the object to the value in the config file while updating through Github
    config_id = models.IntegerField(default=None, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = "challenges"
        db_table = "dataset_split"


class ChallengePhase(TimeStampedModel):

    """Model representing a Challenge Phase"""

    def __init__(self, *args, **kwargs):
        super(ChallengePhase, self).__init__(*args, **kwargs)
        self._original_test_annotation = self.test_annotation

    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    leaderboard_public = models.BooleanField(default=False)
    start_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Start Date (UTC)", db_index=True
    )
    end_date = models.DateTimeField(
        null=True, blank=True, verbose_name="End Date (UTC)", db_index=True
    )
    challenge = models.ForeignKey("Challenge", on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    is_submission_public = models.BooleanField(default=False)
    annotations_uploaded_using_cli = models.BooleanField(default=False)
    test_annotation = models.FileField(
        upload_to=RandomFileName("test_annotations"), null=True, blank=True
    )
    max_submissions_per_day = models.PositiveIntegerField(
        default=100000, db_index=True
    )
    max_submissions_per_month = models.PositiveIntegerField(
        default=100000, db_index=True
    )
    max_submissions = models.PositiveIntegerField(
        default=100000, db_index=True
    )
    max_concurrent_submissions_allowed = models.PositiveIntegerField(default=3)
    codename = models.CharField(max_length=100, default="Phase Code Name")
    dataset_split = models.ManyToManyField(
        DatasetSplit, blank=True, through="ChallengePhaseSplit"
    )
    allowed_email_ids = ArrayField(
        models.TextField(null=True, blank=True),
        default=list,
        blank=True,
        null=True,
    )
    slug = models.SlugField(max_length=200, null=True, unique=True)
    environment_image = models.CharField(
        max_length=2128, null=True, blank=True
    )  # Max length of repository name and tag is 2000 and 128 respectively
    allowed_submission_file_types = models.CharField(
        max_length=200, default=".json, .zip, .txt, .tsv, .gz, .csv, .h5, .npy"
    )
    # Flag to restrict user to select only one submission for leaderboard
    is_restricted_to_select_one_submission = models.BooleanField(default=False)
    # Store the schema for the submission meta attributes of this challenge phase.
    submission_meta_attributes = JSONField(default=None, blank=True, null=True)
    # Flag to allow reporting partial metrics for submission evaluation
    is_partial_submission_evaluation_enabled = models.BooleanField(
        default=False
    )
    # Id in the challenge config file. Needed to map the object to the value in the config file while updating through Github
    config_id = models.IntegerField(default=None, blank=True, null=True)
    # Store the default metadata for a submission meta attributes of a challenge phase.
    default_submission_meta_attributes = JSONField(
        default=None, blank=True, null=True
    )

    class Meta:
        app_label = "challenges"
        db_table = "challenge_phase"
        unique_together = (("codename", "challenge"),)

    def __str__(self):
        """Returns the name of Phase"""
        return self.name

    def get_start_date(self):
        """Returns the start date of Phase"""
        return self.start_date

    def get_end_date(self):
        """Returns the end date of Challenge"""
        return self.end_date

    @property
    def is_active(self):
        """Returns if the challenge is active or not"""
        if self.start_date < timezone.now() and self.end_date > timezone.now():
            return True
        return False

    def save(self, *args, **kwargs):

        # If the max_submissions_per_day is less than the max_concurrent_submissions_allowed.
        if (
            self.max_submissions_per_day
            < self.max_concurrent_submissions_allowed
        ):
            self.max_concurrent_submissions_allowed = (
                self.max_submissions_per_day
            )

        challenge_phase_instance = super(ChallengePhase, self).save(
            *args, **kwargs
        )
        return challenge_phase_instance


class Leaderboard(TimeStampedModel):

    schema = JSONField()
    # Id in the challenge config file. Needed to map the object to the value in the config file while updating through Github
    config_id = models.IntegerField(default=None, blank=True, null=True)

    def __str__(self):
        return "{}".format(self.id)

    class Meta:
        app_label = "challenges"
        db_table = "leaderboard"


class ChallengePhaseSplit(TimeStampedModel):

    # visibility options
    HOST = 1
    OWNER_AND_HOST = 2
    PUBLIC = 3

    VISIBILITY_OPTIONS = (
        (HOST, "host"),
        (OWNER_AND_HOST, "owner and host"),
        (PUBLIC, "public"),
    )

    challenge_phase = models.ForeignKey(
        "ChallengePhase", on_delete=models.CASCADE
    )
    dataset_split = models.ForeignKey("DatasetSplit", on_delete=models.CASCADE)
    leaderboard = models.ForeignKey("Leaderboard", on_delete=models.CASCADE)
    visibility = models.PositiveSmallIntegerField(
        choices=VISIBILITY_OPTIONS, default=PUBLIC
    )
    leaderboard_decimal_precision = models.PositiveIntegerField(default=2)
    is_leaderboard_order_descending = models.BooleanField(default=True)
    show_leaderboard_by_latest_submission = models.BooleanField(default=False)
    show_execution_time = models.BooleanField(default=False)
    # Allow ordering leaderboard by all metrics
    is_multi_metric_leaderboard = models.BooleanField(default=True)

    def __str__(self):
        return "{0} : {1}".format(
            self.challenge_phase.name, self.dataset_split.name
        )

    class Meta:
        app_label = "challenges"
        db_table = "challenge_phase_split"


class ChallengeTemplate(TimeStampedModel):
    """
    Model to store challenge templates

    Arguments:
        TimeStampedModel {[model class]} -- An abstract base class model that provides self-managed `created_at` and
                                            `modified_at` fields.
    """

    title = models.CharField(max_length=500)
    # Stores the challenge config zip file
    template_file = models.FileField(upload_to=RandomFileName("templates"))
    is_active = models.BooleanField(default=False, db_index=True)
    image = models.ImageField(
        upload_to=RandomFileName("templates/preview-images/"),
        null=True,
        blank=True,
        verbose_name="Template Preview Image",
    )
    dataset = models.CharField(max_length=200, default="")
    # The metrics on which the submissions are evaluated
    eval_metrics = ArrayField(
        models.CharField(max_length=200, blank=True),
        default=get_default_eval_metric,
        blank=True,
    )
    phases = models.IntegerField(null=True, blank=True, default=None)
    splits = models.IntegerField(null=True, blank=True, default=None)
    slug = models.CharField(max_length=500, default="")

    class Meta:
        app_label = "challenges"
        db_table = "challenge_templates"
        ordering = ("-created_at",)

    def __str__(self):
        """Returns the title of challenge template"""
        return self.title


class LeaderboardData(TimeStampedModel):

    challenge_phase_split = models.ForeignKey(
        "ChallengePhaseSplit", on_delete=models.CASCADE
    )
    submission = models.ForeignKey("jobs.Submission", on_delete=models.CASCADE)
    leaderboard = models.ForeignKey("Leaderboard", on_delete=models.CASCADE)
    result = JSONField()
    error = JSONField(null=True, blank=True)

    def __str__(self):
        return "{0} : {1}".format(self.challenge_phase_split, self.submission)

    class Meta:
        app_label = "challenges"
        db_table = "leaderboard_data"


class ChallengeConfiguration(TimeStampedModel):
    """
    Model to store zip file for challenge creation.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.OneToOneField(
        Challenge, null=True, blank=True, on_delete=models.CASCADE
    )
    zip_configuration = models.FileField(
        upload_to=RandomFileName("zip_configuration_files/challenge_zip")
    )
    is_created = models.BooleanField(default=False, db_index=True)
    stdout_file = models.FileField(
        upload_to=RandomFileName("zip_configuration_files/challenge_zip"),
        null=True,
        blank=True,
    )
    stderr_file = models.FileField(
        upload_to=RandomFileName("zip_configuration_files/challenge_zip"),
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "challenges"
        db_table = "challenge_zip_configuration"


class StarChallenge(TimeStampedModel):
    """
    Model to star a challenge
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    is_starred = models.BooleanField(default=False, db_index=True)

    class Meta:
        app_label = "challenges"
        db_table = "starred_challenge"


class UserInvitation(TimeStampedModel):
    """
    Model to store invitation status
    """

    ACCEPTED = "accepted"
    PENDING = "pending"

    STATUS_OPTIONS = ((ACCEPTED, ACCEPTED), (PENDING, PENDING))
    email = models.EmailField(max_length=200)
    invitation_key = models.CharField(max_length=200)
    status = models.CharField(
        max_length=30, choices=STATUS_OPTIONS, db_index=True
    )
    challenge = models.ForeignKey(
        Challenge, related_name="challenge", on_delete=models.CASCADE
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(ChallengeHost, on_delete=models.CASCADE)

    class Meta:
        app_label = "challenges"
        db_table = "invite_user_to_challenge"

    def __str__(self):
        """Returns the email of the user"""
        return self.email


class ChallengeEvaluationCluster(TimeStampedModel):
    """Model to store the config for Kubernetes cluster for a challenge

    Arguments:
        TimeStampedModel {[model class]} -- An abstract base class model that provides self-managed `created_at` and
                                            `modified_at` fields.
    """

    challenge = models.OneToOneField(Challenge, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, unique=True, db_index=True)
    cluster_endpoint = models.URLField(max_length=200, blank=True, null=True)
    cluster_ssl = models.TextField(null=True, blank=True)
    cluster_yaml = models.FileField(
        upload_to=RandomFileName("cluster_yaml"), blank=True, null=True
    )
    kube_config = models.FileField(
        upload_to=RandomFileName("kube_config"), blank=True, null=True
    )
    eks_arn_role = models.CharField(max_length=512, null=True, blank=True)
    node_group_arn_role = models.CharField(
        max_length=512, null=True, blank=True
    )
    ecr_all_access_policy_arn = models.CharField(
        max_length=512, null=True, blank=True
    )
    vpc_id = models.CharField(max_length=512, null=True, blank=True)
    subnet_1_id = models.CharField(max_length=512, null=True, blank=True)
    subnet_2_id = models.CharField(max_length=512, null=True, blank=True)
    security_group_id = models.CharField(max_length=512, null=True, blank=True)
    internet_gateway_id = models.CharField(
        max_length=512, null=True, blank=True
    )
    route_table_id = models.CharField(max_length=512, null=True, blank=True)
    efs_security_group_id = models.CharField(
        max_length=512, null=True, blank=True
    )
    efs_id = models.CharField(max_length=512, null=True, blank=True)
    efs_creation_token = models.CharField(
        max_length=256, null=True, blank=True
    )
    efs_mount_target_ids = ArrayField(
        models.CharField(max_length=256, blank=True), default=list, blank=True
    )

    class Meta:
        app_label = "challenges"
        db_table = "challenge_evaluation_cluster"


class PWCChallengeLeaderboard(TimeStampedModel):
    """
    Model to store the challenge mapping with area, task and dataset of papers with code (PWC)
    (https://paperswithcode.com/)

    Arguments:
        TimeStampedModel {[model class]} -- An abstract base class model that provides self-managed `created_at` and
                                            `modified_at` fields.
    """

    phase_split = models.OneToOneField(
        "ChallengePhaseSplit", on_delete=models.CASCADE
    )
    area = models.CharField(max_length=200, default="", db_index=True)
    task = models.CharField(max_length=200, default="", db_index=True)
    dataset = models.CharField(max_length=200, default="", db_index=True)
    enable_sync = models.BooleanField(
        default=True,
        verbose_name="Enable leaderboard sync to PWC",
        db_index=True,
    )

    class Meta:
        app_label = "challenges"
        db_table = "pwc_challenge_leaderboard"
