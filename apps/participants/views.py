from django.contrib.auth.models import User

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.response import Response
from rest_framework_expiring_authtoken.authentication import (
    ExpiringTokenAuthentication,
)
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import HasVerifiedEmail
from base.utils import team_paginated_queryset
from challenges.models import Challenge, ChallengePhase
from challenges.serializers import ChallengeSerializer
from challenges.utils import (
    get_challenge_model,
    get_participant_model,
    is_user_in_allowed_email_domains,
    is_user_in_blocked_email_domains,
)
from jobs.models import Submission
from hosts.utils import is_user_a_host_of_challenge
from .filters import ParticipantTeamsFilter
from .models import Participant, ParticipantTeam
from .serializers import (
    InviteParticipantToTeamSerializer,
    ParticipantTeamSerializer,
    ChallengeParticipantTeam,
    ChallengeParticipantTeamList,
    ChallengeParticipantTeamListSerializer,
    ParticipantTeamDetailSerializer,
)
from .utils import (
    get_list_of_challenges_for_participant_team,
    get_list_of_challenges_participated_by_a_user,
    get_participant_team_of_user_for_a_challenge,
    has_user_participated_in_challenge,
    is_user_part_of_participant_team,
    is_user_creator_of_participant_team,
)


@api_view(["GET", "POST"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes(
    (
        JWTAuthentication,
        ExpiringTokenAuthentication,
    )
)
def participant_team_list(request):

    if request.method == "GET":
        participant_teams_id = Participant.objects.filter(
            user_id=request.user
        ).values_list("team_id", flat=True)
        participant_teams = ParticipantTeam.objects.filter(
            id__in=participant_teams_id
        ).order_by("-id")
        filtered_teams = ParticipantTeamsFilter(
            request.GET, queryset=participant_teams
        )
        paginator, result_page = team_paginated_queryset(
            filtered_teams.qs, request
        )
        serializer = ParticipantTeamDetailSerializer(result_page, many=True)
        response_data = serializer.data
        return paginator.get_paginated_response(response_data)

    elif request.method == "POST":
        serializer = ParticipantTeamSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            participant_team = serializer.instance
            participant = Participant(
                user=request.user,
                status=Participant.SELF,
                team=participant_team,
            )
            participant.save()
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def get_participant_team_challenge_list(request, participant_team_pk):
    """
    Returns a challenge list in which the participant team has participated.
    """
    try:
        participant_team = ParticipantTeam.objects.get(pk=participant_team_pk)
    except ParticipantTeam.DoesNotExist:
        response_data = {"error": "تیم شرکت کننده وجود ندارد"}
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        challenge = Challenge.objects.filter(
            participant_teams=participant_team
        ).order_by("-id")
        paginator, result_page = team_paginated_queryset(challenge, request)
        serializer = ChallengeSerializer(
            result_page, many=True, context={"request": request}
        )
        response_data = serializer.data
        return paginator.get_paginated_response(response_data)


@api_view(["GET", "PUT", "PATCH"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def participant_team_detail(request, pk):
    try:
        participant_team = ParticipantTeam.objects.get(pk=pk)
    except ParticipantTeam.DoesNotExist:
        response_data = {"error": "تیم شرکت کننده وجود ندارد"}
        return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

    if request.method == "GET":
        if not is_user_part_of_participant_team(
                request.user, participant_team
        ):
            response_data = {
                "error": "با عرض پوزش، شما مجاز به مشاهده جزئیات تیم نیستید."
            }
            return Response(response_data, status=status.HTTP_403_FORBIDDEN)

        serializer = ParticipantTeamDetailSerializer(participant_team)
        response_data = serializer.data
        return Response(response_data, status=status.HTTP_200_OK)

    elif request.method in ["PUT", "PATCH"]:

        if request.method == "PATCH":
            if not is_user_creator_of_participant_team(
                    request.user, participant_team
            ):
                response_data = {
                    "error": "شما مجاز به تغییر جزئیات تیم نیستید!"
                }
                return Response(
                    response_data, status=status.HTTP_403_FORBIDDEN
                )

            serializer = ParticipantTeamSerializer(
                participant_team,
                data=request.data,
                context={"request": request},
                partial=True,
            )
        else:
            serializer = ParticipantTeamSerializer(
                participant_team,
                data=request.data,
                context={"request": request},
            )
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            errors = "\n".join(serializer.errors)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def invite_participant_to_team(request, pk):
    try:
        participant_team = ParticipantTeam.objects.get(pk=pk)
    except ParticipantTeam.DoesNotExist:
        response_data = {"error": "تیم شرکت کننده وجود ندارد"}
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    if not is_user_part_of_participant_team(request.user, participant_team):
        response_data = {"error": "شما عضو این تیم نیستید!"}
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

    email = request.data.get("email")
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        response_data = {
            "error": "کاربر با این آدرس ایمیل وجود ندارد!"
        }
        return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

    participant = Participant.objects.filter(team=participant_team, user=user)
    if participant.exists():
        response_data = {"error": "کاربر در حال حاضر بخشی از تیم است!"}
        return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

    invited_user_participated_challenges = (
        get_list_of_challenges_participated_by_a_user(user).values_list(
            "id", flat=True
        )
    )
    team_participated_challenges = get_list_of_challenges_for_participant_team(
        [participant_team]
    ).values_list("id", flat=True)

    if set(invited_user_participated_challenges) & set(
            team_participated_challenges
    ):
        """
            بررسی کنید که آیا کاربر قبلاً در مسابقه هایی شرکت کرده است 
            که شرکت کننده دعوت کننده در آن شرکت کرده است.
             اگر اینطور باشد، کاربر نمی تواند دعوت شود
             زیرا نمی تواند از طریق دو تیم در مسابقه شرکت کند.
        """
        response_data = {
            "error": "با عرض پوزش، کاربر دعوت شده قبلاً در حداقل یکی از مسابقه هایی"
                     " که شما قبلاً بخشی از آن هستید شرکت کرده است."
                     " لطفاً سعی کنید یک تیم جدید ایجاد کنید و سپس دعوت کنید."
        }
        return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

    if len(team_participated_challenges) > 0:
        for challenge_pk in team_participated_challenges:
            challenge = get_challenge_model(challenge_pk)

            if len(challenge.banned_email_ids) > 0:
                # Check if team participants emails are banned
                for (
                        participant_email
                ) in participant_team.get_all_participants_email():
                    if participant_email in challenge.banned_email_ids:
                        message = "شما نمی توانید دعوت کنید زیرا عضوی از تیم {} هستید" \
                                  " و تیم از این مسابقه محروم شده است." \
                                  " لطفاً با میزبان مسابقه تماس بگیرید."
                        response_data = {
                            "error": message.format(participant_team.team_name)
                        }
                        return Response(
                            response_data,
                            status=status.HTTP_406_NOT_ACCEPTABLE,
                        )

                # Check if invited user is banned
                if email in challenge.banned_email_ids:
                    message = "شما نمی توانید دعوت کنید زیرا عضوی از تیم {} هستید" \
                              " و تیم از این مسابقه محروم شده است." \
                              " لطفاً با میزبان مسابقه تماس بگیرید."
                    response_data = {"error": message}
                    return Response(
                        response_data, status=status.HTTP_406_NOT_ACCEPTABLE
                    )

            # Check if user is in allowed list.
            if len(challenge.allowed_email_domains) > 0:
                if not is_user_in_allowed_email_domains(email, challenge_pk):
                    message = "با عرض پوزش، کاربران دارای {} دامنه(های) ایمیل فقط مجاز به شرکت در این مسابقه هستند."
                    domains = ""
                    for domain in challenge.allowed_email_domains:
                        domains = "{}{}{}".format(domains, "/", domain)
                    domains = domains[1:]
                    response_data = {"error": message.format(domains)}
                    return Response(
                        response_data, status=status.HTTP_406_NOT_ACCEPTABLE
                    )

            # Check if user is in blocked list.
            if is_user_in_blocked_email_domains(email, challenge_pk):
                message = "با عرض پوزش، کاربران دارای {} دامنه(های) ایمیل مجاز به شرکت در این مسابقه نیستند."
                domains = ""
                for domain in challenge.blocked_email_domains:
                    domains = "{}{}{}".format(domains, "/", domain)
                domains = domains[1:]
                response_data = {"error": message.format(domains)}
                return Response(
                    response_data, status=status.HTTP_406_NOT_ACCEPTABLE
                )

    serializer = InviteParticipantToTeamSerializer(
        data=request.data,
        context={"participant_team": participant_team, "request": request},
    )

    if serializer.is_valid():
        serializer.save()
        response_data = {
            "message": "کاربر با موفقیت به تیم اضافه شد!"
        }
        return Response(response_data, status=status.HTTP_202_ACCEPTED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def delete_participant_from_team(request, participant_team_pk, participant_pk):
    """
    Deletes a participant from a Participant Team
    """
    try:
        participant_team = ParticipantTeam.objects.get(pk=participant_team_pk)
    except ParticipantTeam.DoesNotExist:
        response_data = {"error": "تیم شرکت کننده وجود ندارد"}
        return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

    try:
        participant = Participant.objects.get(pk=participant_pk)
    except Participant.DoesNotExist:
        response_data = {"error": "شرکت کننده وجود ندارد"}
        return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

    if participant_team.created_by == request.user:

        if (
                participant.user == request.user
        ):  # when the user tries to remove himself
            response_data = {
                "error": "از آنجایی که مدیر هستید، مجاز به حذف خود نیستید. لطفا اگر می خواهید این تیم را حذف کنید!"
            }  # noqa: ignore=E501
            return Response(
                response_data, status=status.HTTP_406_NOT_ACCEPTABLE
            )
        else:
            participant.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
    else:
        response_data = {
            "error": "متأسفیم، شما مجوز حذف این شرکت‌کننده را ندارید"
        }
        return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def get_teams_and_corresponding_challenges_for_a_participant(
        request, challenge_pk
):
    """
    Returns list of teams and corresponding challenges for a participant
    """
    # first get list of all the participants and teams related to the user
    participant_objs = Participant.objects.filter(
        user=request.user
    ).prefetch_related("team")

    is_challenge_host = is_user_a_host_of_challenge(
        user=request.user, challenge_pk=challenge_pk
    )

    challenge_participated_teams = []
    for participant_obj in participant_objs:
        participant_team = participant_obj.team

        challenges = Challenge.objects.filter(
            participant_teams=participant_team
        )

        if challenges.count():
            for challenge in challenges:
                challenge_participated_teams.append(
                    ChallengeParticipantTeam(challenge, participant_team)
                )
        else:
            challenge = None
            challenge_participated_teams.append(
                ChallengeParticipantTeam(challenge, participant_team)
            )
    serializer = ChallengeParticipantTeamListSerializer(
        ChallengeParticipantTeamList(challenge_participated_teams)
    )
    response_data = serializer.data
    response_data["is_challenge_host"] = is_challenge_host
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def remove_self_from_participant_team(request, participant_team_pk):
    """
    A user can remove himself from the participant team.
    """
    try:
        participant_team = ParticipantTeam.objects.get(pk=participant_team_pk)
    except ParticipantTeam.DoesNotExist:
        response_data = {"error": "تیم شرکت کننده وجود ندارد!"}
        return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

    try:
        participant = Participant.objects.get(
            user=request.user, team=participant_team
        )
    except Participant.DoesNotExist:
        response_data = {"error": "متاسفم، شما به این تیم تعلق ندارید!"}
        return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)

    if get_list_of_challenges_for_participant_team(
            [participant_team]
    ).exists():
        response_data = {
            "error": "متأسفیم، شما نمی توانید این تیم را حذف کنید زیرا در مسابقه(های) شرکت کرده است!"
        }
        return Response(response_data, status=status.HTTP_403_FORBIDDEN)
    else:
        participant.delete()
        participants = Participant.objects.filter(team=participant_team)
        if participants.count() == 0:
            participant_team.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def get_participant_team_details_for_challenge(request, challenge_pk):
    """
    API to get the participant team detail

    Arguments:
        request {HttpRequest} -- The request object
        challenge_pk {[int]} -- Challenge primary key

    Returns:
        {dict} -- Participant team detail that has participated in the challenge
    """

    challenge = get_challenge_model(challenge_pk)
    if has_user_participated_in_challenge(request.user, challenge_pk):
        participant_team = get_participant_team_of_user_for_a_challenge(
            request.user, challenge_pk
        )
        serializer = ParticipantTeamSerializer(participant_team)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        response_data = {
            "error": f"The user {request.user.username} has not participanted in {challenge.title}"
        }
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    methods=["post"],
    manual_parameters=[
        openapi.Parameter(
            name="challenge_pk",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_NUMBER,
            description="Challenge pk",
            required=True,
        ),
        openapi.Parameter(
            name="participant_team_pk",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_NUMBER,
            description="Participant team pk",
            required=True,
        ),
    ],
    operation_id="remove_participant_team_from_challenge",
    responses={
        status.HTTP_200_OK: openapi.Response(""),
        status.HTTP_400_BAD_REQUEST: openapi.Response(
            "{'error': 'تیم در مسابقه شرکت نکرده است'}"
        ),
        status.HTTP_401_UNAUTHORIZED: openapi.Response(
            "{'error': 'متأسفیم، شما مجوز حذف این تیم شرکت کننده را ندارید'}"
        )
    },
)
@api_view(["POST"])
@throttle_classes([UserRateThrottle])
@permission_classes((permissions.IsAuthenticated, HasVerifiedEmail))
@authentication_classes((JWTAuthentication, ExpiringTokenAuthentication))
def remove_participant_team_from_challenge(
        request, challenge_pk, participant_team_pk
):
    """
    API to remove the participant team from a challenge

    Arguments:
        request {HttpRequest} -- The request object
        challenge_pk {[int]} -- Challenge primary key
        participant_team_pk {[int]} -- Participant team primary key

    Returns:
        Response Object -- An object containing api response
    """
    challenge = get_challenge_model(challenge_pk)

    participant_team = get_participant_model(participant_team_pk)

    if participant_team.created_by == request.user:
        if participant_team.challenge_set.filter(id=challenge_pk).exists():
            challenge_phases = ChallengePhase.objects.filter(
                challenge=challenge
            )
            for challenge_phase in challenge_phases:
                submissions = Submission.objects.filter(
                    participant_team=participant_team_pk,
                    challenge_phase=challenge_phase,
                )
                if submissions.count() > 0:
                    response_data = {
                        "error": "حذف تیم ممکن نیست زیرا قبلاً برای مسابقه ارسال کرده اید"
                    }
                    return Response(
                        response_data, status=status.HTTP_400_BAD_REQUEST
                    )

            challenge.participant_teams.remove(participant_team)
            return Response(status=status.HTTP_200_OK)
        else:
            response_data = {
                "error": "تیم در مسابقه شرکت نکرده است"
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    else:
        response_data = {
            "error": "متأسفیم، شما مجوز حذف این تیم شرکت کننده را ندارید"
        }
        return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
