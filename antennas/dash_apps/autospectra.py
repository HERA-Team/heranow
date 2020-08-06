"""A dash application to plot autospectra."""
import re

import copy
import numpy as np
import pandas as pd

import lttb

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from ..models import AutoSpectra, AntennaStatus, AprioriStatus


max_points = 1000

app_name = "dash_autospectra"

dash_app = DjangoDash(
    name="dash_autospectra",
    serve_locally=False,
    app_name=app_name,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)

df_full = pd.DataFrame()
df_down = pd.DataFrame()

freqs = np.linspace(50, 250, 8192) * 1e6
spectra = np.cos((freqs - 150e6) / (1e7 * np.pi)) + np.random.normal(
    0, 0.1, size=freqs.size
)
loc = np.random.choice(freqs.size, 10)
spectra[loc] += 5

loc = np.random.choice(freqs.size, 3)
spectra[loc] -= 0.5
last_specta = AutoSpectra.objects.last()
if last_specta is not None:
    all_spectra = AutoSpectra.objects.filter(time=last_specta.time).order_by("antenna")

    for stat in all_spectra:
        ant_stat = (
            AntennaStatus.objects.filter(antenna=stat.antenna).order_by("time").last()
        )
        node = "Unknown"
        if ant_stat is not None:
            match = re.search(r"heraNode(?P<node>\d+)Snap", ant_stat.snap_hostname)
            if match is not None:
                node = int(match.group("node"))

        apriori = "Unknown"
        apriori_stat = (
            AprioriStatus.objects.filter(antenna=stat.antenna).order_by("time").last()
        )
        if apriori_stat is not None:
            apriori = apriori_stat.apriori_status

        _freqs = np.asarray(stat.frequencies) / 1e6
        _spectra = (10 * np.log10(np.ma.masked_invalid(stat.spectra))).filled(-100)
        # _freqs = freqs / 1e6
        # _spectra = spectra
        data = [
            {
                "freqs": f,
                "spectra": d,
                "ant": stat.antenna.ant_number,
                "pol": f"{stat.antenna.polarization}",
                "node": node,
                "apriori": apriori,
            }
            for f, d in zip(_freqs, _spectra)
        ]
        df1 = pd.DataFrame(data)

        df_full = df_full.append(df1)
        downsampled = lttb.downsample(np.stack([_freqs, _spectra,], axis=1), 350,)
        data1 = [
            {
                "freqs": f,
                "spectra": d,
                "ant": stat.antenna.ant_number,
                "pol": f"{stat.antenna.polarization}",
                "node": node,
                "apriori": apriori,
            }
            for f, d in zip(downsampled[:, 0], downsampled[:, 1])
        ]
        df1 = pd.DataFrame(data1)
        df_down = df_down.append(df1)
else:
    _freqs = freqs / 1e6
    _spectra = spectra
    data = [
        {
            "freqs": f,
            "spectra": d,
            "ant": 12,
            "pol": "e",
            "node": 13,
            "apriori": "RF OK",
        }
        for f, d in zip(_freqs, _spectra)
    ]
    df1 = pd.DataFrame(data)

    df_full = df_full.append(df1)
    downsampled = lttb.downsample(
        np.stack([_freqs, _spectra,], axis=1),
        np.round(_freqs.size / 5.0).astype(int) if _freqs.size / 5 > 3 else 3,
    )
    data1 = [
        {
            "freqs": f,
            "spectra": d,
            "ant": 12,
            "pol": "e",
            "node": 13,
            "apriori": "RF OK",
        }
        for f, d in zip(downsampled[:, 0], downsampled[:, 1])
    ]
    df1 = pd.DataFrame(data1)
    df_down = df_down.append(df1)
# Sort according to increasing frequencies and antpols
df_full = df_full.sort_values(["freqs", "ant", "pol"])
df_down = df_down.sort_values(["freqs", "ant", "pol"])

layout = {
    "xaxis": {"title": "Frequency [MHz]"},
    "yaxis": {"title": "Power [dB]"},
    "title": {
        "text": "Autocorrelations",
        "xref": "paper",
        "x": 0.5,
        "font": {"size": 24},
    },
    "autosize": True,
    "showlegend": True,
    "legend": {"x": 1, "y": 1},
    "margin": {"l": 40, "b": 30, "r": 40, "t": 46},
    "hovermode": "closest",
    "uirevision": True,
}


fig = go.Figure()
fig["layout"] = layout
fig2 = go.Figure()
fig2["layout"] = layout
hovertemplate = (
    "%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]"
    "<extra>%{fullData.name}<br>Node: %{meta[0]}<br>Status: %{meta[1]}</extra>"
)

for ant in df_full.ant.unique():
    df1 = df_down[df_down.ant == ant]
    df2 = df_full[df_full.ant == ant]

    for pol in df1.pol.unique():
        antpol = f"{ant}{pol}"
        _df1 = df1[df1.pol == pol]
        trace = go.Scatter(
            x=_df1.freqs,
            y=_df1.spectra,
            name=antpol,
            mode="lines",
            meta=[_df1.node[0], _df1.apriori[0]],
            hovertemplate=hovertemplate,
        )
        fig.add_trace(trace)

        _df2 = df2[df2.pol == pol]
        trace = go.Scatter(
            x=_df2.freqs,
            y=_df2.spectra,
            name=antpol,
            mode="lines",
            meta=[_df2.node[0], _df2.apriori[0]],
            hovertemplate=hovertemplate,
        )
        fig2.add_trace(trace)


dash_app.layout = html.Div(
    [dcc.Graph(figure=fig, id="autospectra", config={"doubleClick": "reset"},),],
)


@dash_app.callback(
    Output("autospectra", "figure"), [Input("autospectra", "relayoutData")]
)
def draw_undecimated_data(selection):
    df_ant = df_full[df_full.ant == df_full.ant.unique()[0]]
    df_ant = df_ant[df_ant.pol == df_ant.pol.unique()[0]]

    if (
        selection is not None
        and "xaxis.range[0]" in selection
        and "xaxis.range[1]" in selection
        and len(
            df_ant[
                (df_ant.freqs >= selection["xaxis.range[0]"])
                & (df_ant.freqs <= selection["xaxis.range[1]"])
            ]
        )
        < max_points
    ):
        return fig2
    else:
        return fig
