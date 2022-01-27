import dash_html_components as html

from .app import app
from .utils import DashRouter, DashNavBar
from .pages import annotateUI, TrainingUI, trainStatusUI, getInferenceUI, testStatusUI, deployUI, deployStatusUI, dlServiceUI
from .components import fa


# Ordered iterable of routes: tuples of (route, layout), where 'route' is a
# string corresponding to path of the route (will be prefixed with Dash's
# 'routes_pathname_prefix' and 'layout' is a Dash Component.
urls = (
    ("", annotateUI.layout),
    ("annotate", annotateUI.layout),
    ("training", TrainingUI.get_layout),
    ("trainStatus", trainStatusUI.layout),
    ("getInference", getInferenceUI.layout),
    ("testStatus", testStatusUI.layout),
    ("deploy", deployUI.layout),
    ("deployStatus", deployStatusUI.layout),
    ("predict", dlServiceUI.layout),
)

# Ordered iterable of navbar items: tuples of `(route, display)`, where `route`
# is a string corresponding to path of the route (will be prefixed with
# 'routes_pathname_prefix') and 'display' is a valid value for the `children`
# keyword argument for a Dash component (ie a Dash Component or a string).
nav_items = (
    # ("annotate", html.Div([fa("fas fa-keyboard"), "Annotate Images"])),
    # ("training", html.Div([fa("fas fa-keyboard"), "Train Model"])),
    # ("trainStatus", html.Div([fa("fas fa-chart-area"), "Training Status"])),
    # ("getInference", html.Div([fa("fas fa-chart-line"), "Testing"])),
    # ("testStatus", html.Div([fa("fas fa-chart-area"), "Testing Status"])),
    # ("deploy", html.Div([fa("fas fa-chart-line"), "Deployment"])),
    # ("predict", html.Div([fa("fas fa-chart-line"), "DLService"])),
)

router = DashRouter(app, urls)
navbar = DashNavBar(app, nav_items)
