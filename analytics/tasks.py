from django.tasks import task

from analytics import services


@task
def recalculate_survey_statistics(*, survey_id: str) -> None:
    services.recalculate_survey(survey_id)
