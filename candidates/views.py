# -*- coding: utf-8 -*-

from django.utils.cache import add_never_cache_headers

from classyviews import ClassyView

class MetaBase:
    @staticmethod
    def get_deadline():
        raise NotImplementedError(
            'Define the get_deadline static method in the overridden meta '
            'class of views inherited from django-candidates')

    @classmethod
    def get_view_permission(cls):
        try: return cls.view_permission
        except AttributeError: pass
        try: return 'view_%s' % cls.model._meta.module_name
        except AttributeError: pass
        raise NotImplementedError(
            'Define either the model attribute, the get_view_permission class '
            'method or the view_permission string attribute in the overridden '
            'meta class of views inherited from django-candidates')

class ApplicationViewBase(ClassyView):
    meta = MetaBase

    def __init__(self, *args, **kwargs):
        super(ApplicationViewBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)

class EditApplicationBase(ApplicationViewBase):
    template_name = 'candidates/application_form.html'

    def GET(self, request, username=''):
        return self.handle_request(request,
                                   None, None, username)

class ConfirmApplicationBase(ApplicationViewBase):
    template_name = 'candidates/confirm_application.html'

    def __init__(self, *args, **kwargs):
        super(ConfirmApplicationBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)

class ApplicationListBase(ApplicationViewBase):
    template_name = 'candidates/application_list.html'

    def __init__(self, *args, **kwargs):
        super(ApplicationListBase, self).__init__(*args, **kwargs)
        add_never_cache_headers(self)
