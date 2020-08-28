"""A dash application to plot autospectra."""
import re

import copy
import uuid
import numpy as np
import pandas as pd

from functools import lru_cache

from astropy.time import Time

import dash
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from ..models import Antenna, AntennaStatus, AprioriStatus, AutoSpectra


def plot_df(
    df,
    mode="spectra",
    cbar_title="dB",
    vmax=None,
    vmin=None,
    colorscale="viridis",
    nodes=None,
):
    if nodes is None or len(nodes) == 0:
        nodes = df.node.unique()

    hovertemplate = "%{text}<extra></extra>"

    layout = {
        "xaxis": {"title": "East-West Position [m]", "constrain": "domain",},
        "yaxis": {
            "title": "North-South Position [m]",
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        "title": {"text": "Per Antpol Stats vs Hex position", "font": {"size": 24},},
        "hoverlabel": {"align": "left"},
        "margin": {"t": 40},
        "autosize": True,
        "showlegend": False,
        "hovermode": "closest",
    }

    cbar_titles = {
        "spectra": "dB",
        "pam_power": "dB",
        "adc_power": "dB",
        "adc_rms": "RMS Linear",
        "fem_imu_theta": "degrees",
        "fem_imu_phi": "degrees",
        "eq_coeffs": "median coefficient",
    }

    fig = go.Figure()

    # df1 = df.fillna(-1)
    # drop rows with None
    if vmin is None:
        vmin = getattr(df, mode).min()
    if vmax is None:
        vmax = getattr(df, mode).max()

    if mode == "adc_rms":
        colorscale = [
            [0.0, "rgb(68,1,84)"],
            [0.2, "rgb(62,74,137)"],
            [0.3, "rgb(38,130,142)"],
            [0.4, "rgb(53,183,121)"],
            [0.5, "rgb(53,183,121)"],
            [0.6, "rgb(53,183,121)"],
            [0.7, "rgb(109,205,89)"],
            [0.8, "rgb(180,222,44)"],
            [1.0, "rgb(253,231,37)"],
        ]
        # some very arbitrary values fine tuned to make green a "good" rms level
        vmin = 0.8
        vmax = 20 / 0.7

    layout.update(
        {
            "coloraxis": {
                "cmin": vmin,
                "cmax": vmax,
                "colorscale": colorscale,
                "colorbar": {"title": cbar_titles[mode], "thickness": 20,},
            },
            "coloraxis2": {"cmin": 0, "cmax": 1, "colorscale": colorscale,},
        }
    )

    fig["layout"] = layout
    df1 = df[df.node.isin(nodes)]
    trace = go.Scatter(
        x=df1[~df1.constructed].antpos_x,
        y=df1[~df1.constructed].antpos_y,
        mode="markers",
        marker={
            "color": df1[~df1.constructed].color,
            "size": 14,
            "symbol": "hexagon",
            "coloraxis": "coloraxis2",
            "opacity": df1[~df1.constructed].opacity,
        },
        text=df1[~df1.constructed].text,
        hovertemplate=hovertemplate,
    )
    fig.add_trace(trace)

    trace = go.Scatter(
        x=df1[df1.constructed].antpos_x,
        y=df1[df1.constructed].antpos_y,
        mode="markers",
        marker={
            "color": getattr(df1[df1.constructed], mode).fillna("orange"),
            "size": 14,
            "coloraxis": "coloraxis",
            "symbol": "hexagon",
            "opacity": df1[df1.constructed].opacity,
        },
        text=df1[df1.constructed].text,
        hovertemplate=hovertemplate,
    )
    fig.add_trace(trace)
    return fig


@lru_cache
def get_data(session_id, n_intervals):
    df = []

    # a shorter variable to help with the text section
    NA = "Unknown"
    last_spectra = AutoSpectra.objects.last()
    auto_time = Time(last_spectra.time, format="datetime")
    if last_spectra is not None:
        all_spectra = AutoSpectra.objects.filter(time=last_spectra.time)
    else:
        all_spectra = None

    pol_list = sorted(Antenna.objects.order_by().values_list("polarization").distinct())
    pol_y_val = {val[0]: cnt for cnt, val in enumerate(pol_list)}
    for antenna in Antenna.objects.all():
        data = {
            "antpos_x": antenna.antpos_enu[0],
            "antpos_y": antenna.antpos_enu[1]
            + 3 * (pol_y_val[antenna.polarization] - 0.5),
            "ant": antenna.ant_number,
            "pol": f"{antenna.polarization}",
            "text": f"{antenna.ant_number}{antenna.polarization}<br>Not Constructed",
            "opacity": 0.2,
            "constructed": antenna.constructed,
            "color": "black",
            "node": "Unknown",
            "apriori": "Unknown",
        }
        stat = AntennaStatus.objects.filter(antenna=antenna).order_by("time").last()
        if stat is None:
            if antenna.constructed:
                # They are actually constructed but with no status they are OFFLINE
                # a little hacky way to get it to display properly out of the DataFrame
                data["constructed"] = False
                data["color"] = "red"
                data["text"] = (
                    f"{antenna.ant_number}{antenna.polarization}<br>Constructed but not online",
                )

        else:
            node = "Unknown"
            match = re.search(r"heraNode(?P<node>\d+)Snap", stat.snap_hostname)
            if match is not None:
                node = int(match.group("node"))

            apriori = "Unknown"
            apriori_stat = (
                AprioriStatus.objects.filter(antenna=stat.antenna)
                .order_by("time")
                .last()
            )
            if apriori_stat is not None:
                apriori = apriori_stat.apriori_status
            if all_spectra is not None:
                try:
                    auto = all_spectra.get(antenna=antenna)
                except AutoSpectra.DoesNotExist:
                    auto = None
                if auto is not None:

                    if auto.eq_coeffs is not None:
                        spectra = auto.spectra / auto.eq_coeffs ** 2
                    else:
                        spectra = auto.spectra
                    spectra = (
                        (10 * np.log10(np.ma.masked_invalid(spectra)))
                        .filled(-100)
                        .mean()
                    )
                else:
                    spectra = None
            else:
                spectra = None

            adc_power = (
                10 * np.log10(stat.adc_power) if stat.adc_power is not None else None
            )
            data.update(
                {
                    "spectra": spectra,
                    "node": node,
                    "apriori": apriori,
                    "pam_power": stat.pam_power,
                    "adc_power": adc_power,
                    "adc_rms": stat.adc_rms,
                    "fem_imu_theta": stat.fem_imu[0],
                    "fem_imu_phi": stat.fem_imu[1],
                    "eq_coeffs": np.median(stat.eq_coeffs)
                    if stat.eq_coeffs is not None
                    else None,
                    "opacity": 1,
                }
            )

            data.update(
                {
                    "text": (
                        f"{antenna.ant_number}{antenna.polarization}<br>"
                        f"Snap: {stat.snap_hostname or NA}<br>"
                        f"PAM: {stat.pam_id or NA}<br>"
                        f"Status: {apriori}<br>"
                        f"Auto  [dB]: {spectra or NA:{'.2f' if spectra else 's'}}<br>"
                        f"PAM [dB]: {stat.pam_power or NA:{'.2f' if stat.pam_power else 's'}}<br>"
                        f"ADC [dB]: {adc_power or NA:{'.2f' if adc_power else 's'}}<br>"
                        f"ADC RMS: {stat.adc_rms or NA:{'.2f' if stat.adc_rms else 's'}}<br>"
                        f"FEM IMU THETA: {stat.fem_imu[0] or NA:{'.2f' if stat.fem_imu[0] else 's'}}<br>"
                        f"FEM IMU PHI: {stat.fem_imu[1] or NA:{'.2f' if stat.fem_imu[1] else 's'}}<br>"
                        f"EQ COEF: {data['eq_coeffs'] or NA}<br>"
                        "Antenna Status "
                        f"{(Time.now() - Time(stat.time, format='datetime')).to_value('hour'):.2f}"
                        " hours old"
                    )
                }
            )
        df.append(data)

    df = pd.DataFrame(df)

    # Sort according to increasing bins and antpols
    if not df.empty:
        df.sort_values(["ant", "pol"], inplace=True)
        df.reset_index(inplace=True, drop=True)
    return df, auto_time


def serve_layout():
    timestamp = Time(0, format="jd")
    init_time_ago = (Time.now() - timestamp).to("min")
    init_time_color = "red"
    session_id = str(uuid.uuid4())

    return html.Div(
        [
            html.Div(session_id, id="session-id", style={"display": "none"}),
            dbc.Row(
                [
                    dbc.Col(
                        daq.BooleanSwitch(
                            id="reload-box",
                            on=False,
                            label="Reload Data",
                            labelPosition="top",
                        ),
                        width=1,
                    ),
                    dbc.Col(
                        html.Div(
                            id="auto-time",
                            children=[
                                html.Span(
                                    "Autocorrelations from ",
                                    style={"font-weight": "bold"},
                                ),
                                html.Span(
                                    f"{init_time_ago.value:.0f} {init_time_ago.unit.long_names[0]}s ago ",
                                    style={
                                        "font-weight": "bold",
                                        "color": init_time_color,
                                    },
                                ),
                                html.Span(
                                    f"({timestamp.iso} JD:{timestamp.jd:.3f})",
                                    style={"font-weight": "bold"},
                                ),
                            ],
                            style={"text-align": "left"},
                        ),
                        width=6,
                    ),
                ],
                justify="center",
                align="center",
            ),
            dbc.Row(
                [
                    html.Label(
                        [
                            "Statistic:",
                            dcc.Dropdown(
                                id="stat-dropdown",
                                options=[
                                    {"label": "Autos", "value": "spectra"},
                                    {"label": "PAM Power", "value": "pam_power"},
                                    {"label": "ADC Power", "value": "adc_power"},
                                    {"label": "ADC RMS", "value": "adc_rms"},
                                    {
                                        "label": "FEM IMU THETA",
                                        "value": "fem_imu_theta",
                                    },
                                    {"label": "FEM IMU PHI", "value": "fem_imu_phi"},
                                    {"label": "EQ COEFFS", "value": "eq_coeffs"},
                                ],
                                multi=False,
                                value="spectra",
                                clearable=False,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "30%"},
                    ),
                    html.Label(
                        [
                            "Node(s):",
                            dcc.Dropdown(
                                id="node-dropdown",
                                options=[{"label": "Unknown Node", "value": "Unknown"}],
                                multi=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "30%"},
                    ),
                ],
                justify="center",
                align="center",
            ),
            dcc.Graph(
                id="graph",
                config={"doubleClick": "reset+autosize"},
                responsive=True,
                style={"height": "90%"},
            ),
            # A timer to re-load data every minute
            # interval value is milliseconds
            dcc.Interval(
                id="interval-component",
                interval=60 * 1000,
                n_intervals=0,
                disabled=True,
            ),
        ],
        style={"height": "100%", "width": "100%"},
    )


app_name = "dash_hexplot"

dash_app = DjangoDash(
    name=app_name,
    serve_locally=False,
    app_name=app_name,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    add_bootstrap_links=True,
)

dash_app.layout = serve_layout


@dash_app.callback(
    Output("interval-component", "disabled"), [Input("reload-box", "on")],
)
def start_reload_counter(reload_box):
    return not reload_box


@dash_app.callback(
    Output("auto-time", "children"),
    [Input("session-id", "children"), Input("interval-component", "n_intervals"),],
)
def update_time_data(session_id, n_intervals):
    df, auto_time = get_data(session_id, n_intervals)

    time_ago = (Time.now() - auto_time).to("min")

    if time_ago.value > 10:
        time_color = "red"
    else:
        time_color = "black"

    if time_ago.value > 60:
        time_ago = time_ago.to("hour")
    if time_ago.value > 24:
        time_ago = time_ago.to("day")

    time_data = [
        html.Span("Autocorrelations from ", style={"font-weight": "bold"}),
        html.Span(
            f"{time_ago.value:.0f} {time_ago.unit.long_names[0]}s ago ",
            style={"font-weight": "bold", "color": time_color,},
        ),
        html.Span(
            f"({auto_time.iso} JD:{auto_time.jd:.3f})", style={"font-weight": "bold"},
        ),
    ]
    return time_data


@dash_app.callback(
    Output("node-dropdown", "options"),
    [Input("session-id", "children"), Input("interval-component", "n_intervals")],
)
def update_node_selection(session_id, n_intervals):
    df, auto_time = get_data(session_id, n_intervals)
    node_labels = [
        {"label": f"Node {node}", "value": node}
        for node in sorted([node for node in df.node.unique() if node != "Unknown"])
    ] + [{"label": "Unknown Node", "value": "Unknown"}]
    return node_labels


@dash_app.callback(
    Output("graph", "figure"),
    [
        Input("stat-dropdown", "value"),
        Input("node-dropdown", "value"),
        Input("session-id", "children"),
        Input("interval-component", "n_intervals"),
    ],
)
def redraw_statistic(stat_value, nodes, session_id, n_intervals):
    df, auto_time = get_data(session_id, n_intervals)
    return plot_df(df, mode=stat_value, nodes=nodes)
