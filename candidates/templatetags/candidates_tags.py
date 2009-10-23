from django import template
register = template.Library()

@register.inclusion_tag('candidates/_field.html')
def application_form_field(field, alt_label=''):
    """
    Print HTML for a field.  Optionally, a label can be supplied that overrides
    the default label generated for the form.

    Example:
    {% display_field form.my_field "My New Label" %}
    """

    if alt_label:
        field.label = alt_label
    return {'field': field}
