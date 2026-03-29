from sqladmin import ModelView

from db.models.exam_request import ExamRequest


class ExamRequestAdmin(ModelView, model=ExamRequest):
    name = "Exam Request"
    name_plural = "Exam Requests"
    icon = "fa-solid fa-inbox"

    column_list = [
        ExamRequest.id,
        ExamRequest.exam_name,
        ExamRequest.email,
        ExamRequest.status,
        ExamRequest.created_at,
    ]
    column_searchable_list = [
        ExamRequest.exam_name,
        ExamRequest.email,
    ]
    column_sortable_list = [
        ExamRequest.id,
        ExamRequest.exam_name,
        ExamRequest.status,
        ExamRequest.created_at,
    ]

    can_create = False
    can_edit   = True
    can_delete = True
    can_export = True
