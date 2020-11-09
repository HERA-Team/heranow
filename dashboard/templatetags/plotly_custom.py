"""Definition of custom django tempalte tags."""
from django import template
from django.template.loader_tags import do_include
from django.template.base import TemplateSyntaxError, Token

from django_plotly_dash.templatetags import plotly_dash

register = template.Library()


@register.inclusion_tag("django_plotly_dash/plotly_direct.html", takes_context=True)
def plotly_direct_app_name(context, name=None, slug=None, da=None):
    """Direct insertion of a Dash app using a names application."""
    da, app = plotly_dash._locate_daapp(context["app_name"], slug, da)

    view_func = app.locate_endpoint_function()

    # Load embedded holder inserted by middleware
    eh = context.request.dpd_content_handler.embedded_holder

    # Need to add in renderer launcher
    renderer_launcher = '<script id="_dash-renderer" type="application/javascript">var renderer = new DashRenderer();</script>'

    app.set_embedded(eh)
    try:
        resp = view_func()
    finally:
        eh.add_scripts(renderer_launcher)
        app.exit_embedded()

    return locals()
