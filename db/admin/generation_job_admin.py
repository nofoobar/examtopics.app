from sqladmin import ModelView

from db.models.generation_job import GenerationJob


class GenerationJobAdmin(ModelView, model=GenerationJob):
    name = "Generation Job"
    name_plural = "Generation Jobs"
    icon = "fa-solid fa-gears"

    column_list = [
        GenerationJob.id,
        GenerationJob.exam_name,
        GenerationJob.status,
        GenerationJob.completed_steps,
        GenerationJob.total_steps,
        GenerationJob.result_exam_id,
        GenerationJob.error,
        GenerationJob.created_at,
    ]
    column_searchable_list = [GenerationJob.exam_name, GenerationJob.status]
    column_sortable_list = [
        GenerationJob.id,
        GenerationJob.status,
        GenerationJob.created_at,
    ]

    can_create = False
    can_edit   = True
    can_delete = True
    can_export = True
