task_definition = """
{{
    "family":"{queue_name}",
    "executionRoleArn":"{EXECUTION_ROLE_ARN}",
    "containerDefinitions":[
        {{
            "name": "{container_name}",
            "image": "{WORKER_IMAGE}",
            "essential": True,
            "environment": [

                {{
                  "name": "CHALLENGE_PK",
                  "value": "{challenge_pk}"
                }},
                {{
                  "name": "CHALLENGE_QUEUE",
                  "value": "{queue_name}"
                }},
                {{
                  "name": "DJANGO_SERVER",
                  "value": "{DJANGO_SERVER}"
                }},
                {{
                  "name": "DJANGO_SETTINGS_MODULE",
                  "value": "settings.{ENV}"
                }},
                {{
                  "name": "DEBUG",
                  "value": "{DEBUG}"
                }},
                {{
                  "name": "EMAIL_HOST",
                  "value": "{EMAIL_HOST}"
                }},
                {{
                  "name": "EMAIL_HOST_PASSWORD",
                  "value": "{EMAIL_HOST_PASSWORD}"
                }},
                {{
                  "name": "EMAIL_HOST_USER",
                  "value": "{EMAIL_HOST_USER}"
                }},
                {{
                  "name": "EMAIL_PORT",
                  "value": "{EMAIL_PORT}"
                }},
                {{
                  "name": "EMAIL_USE_TLS",
                  "value": "{EMAIL_USE_TLS}"
                }},
                {{
                  "name": "MEMCACHED_LOCATION",
                  "value": "{MEMCACHED_LOCATION}"
                }},
                {{
                    "name": "PYTHONUNBUFFERED",
                    "value": "1"
                }},
                {{
                  "name": "RDS_DB_NAME",
                  "value": "{RDS_DB_NAME}"
                }},
                {{
                  "name": "RDS_HOSTNAME",
                  "value": "{RDS_HOSTNAME}"
                }},
                {{
                  "name": "RDS_PASSWORD",
                  "value": "{RDS_PASSWORD}"
                }},
                {{
                  "name": "RDS_USERNAME",
                  "value": "{RDS_USERNAME}"
                }},
                {{
                  "name": "RDS_PORT",
                  "value": "{RDS_PORT}"
                }},
                {{
                  "name": "SECRET_KEY",
                  "value": "{SECRET_KEY}"
                }},
                {{
                  "name": "SENTRY_URL",
                  "value": "{SENTRY_URL}"
                }},
                {{
                    "name": "STATSD_ENDPOINT",
                    "value": "{STATSD_ENDPOINT}"
                }},
                {{
                    "name": "STATSD_PORT",
                    "value": "{STATSD_PORT}"
                }}
            ],
            "workingDirectory": "/code",
            "readonlyRootFilesystem": False,

        }}
    ],
    "requiresCompatibilities":[
        "FARGATE"
    ],
    "cpu": "{CPU}",
    "memory": "{MEMORY}",
}}
"""

task_definition_code_upload_worker = """
{{
    "family":"{queue_name}",
    "executionRoleArn":"{EXECUTION_ROLE_ARN}",
    "containerDefinitions":[
        {{
            "name": "{code_upload_container_name}",
            "image": "{CODE_UPLOAD_WORKER_IMAGE}",
            "essential": True,
            "environment": [

                {{
                  "name": "CLUSTER_NAME",
                  "value": "{cluster_name}"
                }},
                {{
                  "name": "CLUSTER_ENDPOINT",
                  "value": "{cluster_endpoint}"
                }},
                {{
                  "name": "CERTIFICATE",
                  "value": "{certificate}"
                }},
                {{
                  "name": "CIDR",
                  "value": "{CIDR}"
                }},
                {{
                  "name": "QUEUE_NAME",
                  "value": "{queue_name}"
                }},
                {{
                  "name": "EVALAI_API_SERVER",
                  "value": "{EVALAI_API_SERVER}"
                }},

                {{
                    "name": "AUTH_TOKEN",
                    "value": "{auth_token}"
                }},

                {{
                    "name": "EVALAI_DNS",
                    "value": "{EVALAI_DNS}"
                }},

                {{
                    "name": "EFS_ID",
                    "value": "{EFS_ID}"
                }}

            ],
            "workingDirectory": "/code",
            "readonlyRootFilesystem": False,
        }}
    ],
    "requiresCompatibilities":[
        "FARGATE"
    ],
    "cpu": "{CPU}",
    "memory": "{MEMORY}",
}}
"""

task_definition_static_code_upload_worker = """
{{
    "family":"{queue_name}",
    "executionRoleArn":"{EXECUTION_ROLE_ARN}",
    "containerDefinitions":[
        {code_upload_container},
        {submission_container}
    ],
    "requiresCompatibilities":[
        "FARGATE"
    ],
    "cpu": "{CPU}",
    "memory": "{MEMORY}",
}}
"""

container_definition_submission_worker = """
{{
    "name": "{container_name}",
    "image": "{WORKER_IMAGE}",
    "essential": True,
    "environment": [

        {{
            "name": "CHALLENGE_PK",
            "value": "{challenge_pk}"
        }},
        {{
            "name": "CHALLENGE_QUEUE",
            "value": "{queue_name}"
        }},
        {{
            "name": "DJANGO_SERVER",
            "value": "{DJANGO_SERVER}"
        }},
        {{
            "name": "DJANGO_SETTINGS_MODULE",
            "value": "settings.{ENV}"
        }},
        {{
            "name": "DEBUG",
            "value": "{DEBUG}"
        }},
        {{
            "name": "EMAIL_HOST",
            "value": "{EMAIL_HOST}"
        }},
        {{
            "name": "EMAIL_HOST_PASSWORD",
            "value": "{EMAIL_HOST_PASSWORD}"
        }},
        {{
            "name": "EMAIL_HOST_USER",
            "value": "{EMAIL_HOST_USER}"
        }},
        {{
            "name": "EMAIL_PORT",
            "value": "{EMAIL_PORT}"
        }},
        {{
            "name": "EMAIL_USE_TLS",
            "value": "{EMAIL_USE_TLS}"
        }},
        {{
            "name": "MEMCACHED_LOCATION",
            "value": "{MEMCACHED_LOCATION}"
        }},
        {{
            "name": "PYTHONUNBUFFERED",
            "value": "1"
        }},
        {{
            "name": "RDS_DB_NAME",
            "value": "{RDS_DB_NAME}"
        }},
        {{
            "name": "RDS_HOSTNAME",
            "value": "{RDS_HOSTNAME}"
        }},
        {{
            "name": "RDS_PASSWORD",
            "value": "{RDS_PASSWORD}"
        }},
        {{
            "name": "RDS_USERNAME",
            "value": "{RDS_USERNAME}"
        }},
        {{
            "name": "RDS_PORT",
            "value": "{RDS_PORT}"
        }},
        {{
            "name": "SECRET_KEY",
            "value": "{SECRET_KEY}"
        }},
        {{
            "name": "SENTRY_URL",
            "value": "{SENTRY_URL}"
        }},
        {{
            "name": "STATSD_ENDPOINT",
            "value": "{STATSD_ENDPOINT}"
        }},
        {{
            "name": "STATSD_PORT",
            "value": "{STATSD_PORT}"
        }}
    ],
    "workingDirectory": "/code",
    "readonlyRootFilesystem": False,
}}
"""

container_definition_code_upload_worker = """
{{
    "name": "{code_upload_container_name}",
    "image": "{CODE_UPLOAD_WORKER_IMAGE}",
    "essential": True,
    "environment": [
        {{
            "name": "CLUSTER_NAME",
            "value": "{cluster_name}"
        }},
        {{
            "name": "CLUSTER_ENDPOINT",
            "value": "{cluster_endpoint}"
        }},
        {{
            "name": "CERTIFICATE",
            "value": "{certificate}"
        }},
        {{
            "name": "CIDR",
            "value": "{CIDR}"
        }},
        {{
            "name": "QUEUE_NAME",
            "value": "{queue_name}"
        }},
        {{
            "name": "EVALAI_API_SERVER",
            "value": "{EVALAI_API_SERVER}"
        }},

        {{
            "name": "AUTH_TOKEN",
            "value": "{auth_token}"
        }},

        {{
            "name": "EVALAI_DNS",
            "value": "{EVALAI_DNS}"
        }},
        {{
            "name": "EFS_ID",
            "value": "{EFS_ID}"
        }},
        {{
            "name": "STATSD_ENDPOINT",
            "value": "{STATSD_ENDPOINT}"
        }},
        {{
            "name": "STATSD_PORT",
            "value": "{STATSD_PORT}"
        }}

    ],
    "workingDirectory": "/code",
    "readonlyRootFilesystem": False,
}}
"""

service_definition = """
{{
    "cluster":"{CLUSTER}",
    "serviceName":"{service_name}",
    "taskDefinition":"{task_def_arn}",
    "desiredCount":1,
    "clientToken":"{client_token}",
    "launchType":"FARGATE",
    "platformVersion":"LATEST",

    "schedulingStrategy":"REPLICA",
    "deploymentController":{{
        "type": "ECS"
    }},
    "deploymentConfiguration":{{
        "deploymentCircuitBreaker":{{
            "enable": True,
            "rollback": False
        }}
    }}
}}
"""

update_service_args = """
{{
    "cluster":"{CLUSTER}",
    "service":"{service_name}",
    "desiredCount":{num_of_tasks},
    "taskDefinition":"{task_def_arn}",
    "forceNewDeployment":{force_new_deployment}
}}
"""

delete_service_args = """
{{
    "cluster": "{CLUSTER}",
    "service": "{service_name}",
    "force": False
}}
"""
