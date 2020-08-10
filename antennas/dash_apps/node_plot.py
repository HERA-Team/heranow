"""A dash application to plot autospectra."""
import re

import copy
import numpy as np
import pandas as pd

from astropy.time import Time

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from ..models import Antenna, AntennaStatus, AprioriStatus, AutoSpectra


def plot_df(
    df, mode="spectra", cbar_title="dB", vmax=None, vmin=None, colorscale="viridis"
):
    hovertemplate = "%{text}<extra></extra>"

    layout = {
        "xaxis": {
            "title": "Node Number",
            "type": "category",
            "showgrid": False,
            "zeroline": False,
        },
        "yaxis": {"showticklabels": False, "showgrid": False, "zeroline": False},
        "title": {"text": "Per Antpol Stats vs Node", "font": {"size": 24}},
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

    fig["layout"] = layout
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

    for node in df.node.unique():
        df1 = df[df.node == node]
        df1.reset_index(inplace=True)

        trace = go.Scatter(
            x=df1.node,
            y=df1.index,
            mode="markers",
            marker={
                "color": getattr(df, mode).fillna("orange"),
                "size": 14,
                "cmin": vmin,
                "cmax": vmax,
                "colorscale": colorscale,
                "colorbar": {"thickness": 20, "title": cbar_titles[mode]},
                "symbol": "hexagon",
            },
            text=df1.text,
            hovertemplate=hovertemplate,
        )
        fig.add_trace(trace)
    return fig


app_name = "dash_nodeplot"

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
df = pd.DataFrame()

# a shorter variable to help with the text section
NA = "Unknown"
last_spectra = AutoSpectra.objects.last()
auto_time = Time(last_spectra.time, format="datetime")
if last_spectra is not None:
    all_spectra = AutoSpectra.objects.filter(time=last_spectra.time)
else:
    all_spectra = None

pol_list = list(Antenna.objects.order_by().values_list("polarization").distinct())
pol_y_val = {val[0]: cnt for cnt, val in enumerate(pol_list)}
for antenna in Antenna.objects.all():
    data = {
        "antpos_x": antenna.antpos_enu[0],
        "antpos_y": antenna.antpos_enu[1] + 3 * (pol_y_val[antenna.polarization] - 0.5),
        "ant": antenna.ant_number,
        "pol": f"{antenna.polarization}",
        "text": f"{antenna.ant_number}{antenna.polarization}<br>Not Constructed",
    }
    stat = AntennaStatus.objects.filter(antenna=antenna).order_by("time").last()
    if stat is not None:
        node = "Unknown"
        snap = "Unknown"
        match = re.search(
            r"heraNode(?P<node>\d+)Snap(?P<snap>\d{1,2})", stat.snap_hostname
        )
        if match is not None:
            node = int(match.group("node"))
            snap = int(match.group("snap"))

        apriori = "Unknown"
        apriori_stat = (
            AprioriStatus.objects.filter(antenna=stat.antenna).order_by("time").last()
        )
        if apriori_stat is not None:
            apriori = apriori_stat.apriori_status
        if all_spectra is not None:
            try:
                auto = all_spectra.get(antenna=antenna)
            except AutoSpectra.DoesNotExist:
                auto = None
            if auto is not None:
                spectra = (10 * np.log10(np.ma.masked_invalid(auto.spectra))).mean()
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
                "snap": snap,
                "apriori": apriori,
                "pam_power": stat.pam_power,
                "adc_power": adc_power,
                "adc_rms": stat.adc_rms,
                "fem_imu_theta": stat.fem_imu[0],
                "fem_imu_phi": stat.fem_imu[1],
                "eq_coeffs": np.median(stat.eq_coeffs)
                if stat.eq_coeffs is not None
                else None,
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

    df = df.append([data])


# Sort according to increasing bins and antpols
if not df.empty:
    df = df.sort_values(["node", "snap", "ant", "pol"])

dash_app.layout = html.Div(
    [
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
                                {"label": "FEM IMU THETA", "value": "fem_imu_theta"},
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
            ],
            justify="center",
            align="center",
            style={"height": "10%"},
        ),
        dcc.Graph(
            figure=plot_df(df),
            id="dash_app",
            config={"doubleClick": "reset"},
            responsive=True,
            style={"height": "90%"},
        ),
    ],
    style={"height": "100%", "width": "100%"},
)


@dash_app.callback(
    Output("dash_app", "figure"), [Input("stat-dropdown", "value"),],
)
def redraw_statistic(stat_value):
    return plot_df(df, mode=stat_value)
