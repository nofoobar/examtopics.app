from sqladmin import ModelView

from db.models.exam import Vendor, Exam, Test, Question


class VendorAdmin(ModelView, model=Vendor):
    name = "Vendor"
    name_plural = "Vendors"
    icon = "fa-solid fa-building"

    column_list = [
        Vendor.id,
        Vendor.name,
        Vendor.slug,
        Vendor.is_active,
        Vendor.created_at,
    ]
    column_searchable_list = [Vendor.name, Vendor.slug]
    column_sortable_list  = [Vendor.id, Vendor.name, Vendor.created_at]

    can_create = True
    can_edit   = True
    can_delete = True
    can_export = True


class ExamAdmin(ModelView, model=Exam):
    name = "Exam"
    name_plural = "Exams"
    icon = "fa-solid fa-file-lines"

    column_list = [
        Exam.id,
        Exam.name,
        Exam.exam_code,
        Exam.slug,
        Exam.vendor_id,
        Exam.is_featured,
        Exam.is_active,
        Exam.created_at,
    ]
    column_searchable_list = [Exam.name, Exam.slug, Exam.exam_code]
    column_sortable_list   = [Exam.id, Exam.name, Exam.created_at, Exam.is_featured]

    can_create = True
    can_edit   = True
    can_delete = True
    can_export = True


class TestAdmin(ModelView, model=Test):
    name = "Test"
    name_plural = "Tests"
    icon = "fa-solid fa-list-check"

    column_list = [
        Test.id,
        Test.name,
        Test.slug,
        Test.exam_id,
        Test.is_active,
        Test.created_at,
    ]
    column_searchable_list = [Test.name, Test.slug]
    column_sortable_list   = [Test.id, Test.name, Test.exam_id, Test.created_at]

    can_create = True
    can_edit   = True
    can_delete = True
    can_export = True


class QuestionAdmin(ModelView, model=Question):
    name = "Question"
    name_plural = "Questions"
    icon = "fa-solid fa-circle-question"

    column_list = [
        Question.id,
        Question.question_type,
        Question.domain,
        Question.test_id,
        Question.is_active,
        Question.created_at,
    ]
    # Don't show full question text in list — can be very long
    column_searchable_list = [Question.domain, Question.source]
    column_sortable_list   = [Question.id, Question.question_type, Question.test_id, Question.created_at]

    can_create = True
    can_edit   = True
    can_delete = True
    can_export = True
