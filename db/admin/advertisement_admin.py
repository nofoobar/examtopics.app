from sqladmin import ModelView

from db.models.advertisement import Advertisement


class AdvertisementAdmin(ModelView, model=Advertisement):
    name = "Advertisement"
    name_plural = "Advertisements"
    icon = "fa-solid fa-rectangle-ad"

    column_list = [
        Advertisement.id,
        Advertisement.title,
        Advertisement.position,
        Advertisement.is_generic_ad,
        Advertisement.exam_id,
        Advertisement.notify_on_click,
        Advertisement.click_count,
        Advertisement.is_active,
        Advertisement.starts_at,
        Advertisement.ends_at,
        Advertisement.created_at,
    ]
    column_searchable_list = [Advertisement.title, Advertisement.link]
    column_sortable_list   = [
        Advertisement.id,
        Advertisement.title,
        Advertisement.click_count,
        Advertisement.is_active,
        Advertisement.created_at,
    ]

    # Show link + image_url in the detail/edit form but keep list clean
    column_details_exclude_list = []

    can_create = True
    can_edit   = True
    can_delete = True
    can_export = True
