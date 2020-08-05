"""A dash application to plot autospectra."""
import lttb
import copy
import numpy as np
import pandas as pd

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from ..models import AutoSpectra


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
last_status = AutoSpectra.objects.last()
if last_status is not None:
    all_stats = AutoSpectra.objects.filter(time=last_status.time).order_by("antenna")

    for stat in all_stats:
        # _freqs = np.asarray(stat.frequencies) / 1e6
        # _spectra = 10 * np.log10(np.ma.masked_invalid(stat.spectra)).filled(None)
        _freqs = freqs / 1e6
        _spectra = spectra
        data = [
            {
                "freqs": f,
                "spectra": d,
                "antpol": f"{stat.antenna.ant_number}{stat.antenna.polarization}",
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
                "antpol": f"{stat.antenna.ant_number}{stat.antenna.polarization}",
            }
            for f, d in zip(downsampled[:, 0], downsampled[:, 1])
        ]
        df1 = pd.DataFrame(data1)
        df_down = df_down.append(df1)
else:
    _freqs = freqs / 1e6
    _spectra = spectra
    data = [
        {"freqs": f, "spectra": d, "antpol": "12e",} for f, d in zip(_freqs, _spectra)
    ]
    df1 = pd.DataFrame(data)

    df_full = df_full.append(df1)
    downsampled = lttb.downsample(
        np.stack([_freqs, _spectra,], axis=1),
        np.round(_freqs.size / 5.0).astype(int) if _freqs.size / 5 > 3 else 3,
    )
    data1 = [
        {"freqs": f, "spectra": d, "antpol": "12e",}
        for f, d in zip(downsampled[:, 0], downsampled[:, 1])
    ]
    df1 = pd.DataFrame(data1)
    df_down = df_down.append(df1)
# Sort according to increasing frequencies and antpols
df_full = df_full.sort_values(["freqs", "antpol"])
df_down = df_down.sort_values(["freqs", "antpol"])

fig = go.Figure()
for antpol in df_full.antpol.unique():
    df1 = df_down[df_down.antpol == antpol]
    trace = go.Scatter(
        x=df1.freqs,
        y=df1.spectra,
        name=antpol,
        mode="lines",
        meta=[7],
        hovertemplate="%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]<extra>%{fullData.name}<br>node %{meta[0]}</extra>",
    )
    fig.add_trace(trace)

    # df1 = df_full[df_full.antpol == antpol]
    # trace = go.Scatter(
    #     x=df1.freqs,
    #     y=df1.spectra,
    #     name=antpol,
    #     mode="lines",
    #     hovertemplate="%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]",
    # )
    # fig.add_trace(trace)

fig.update_layout(
    xaxis={"title": "Frequency [MHz]"},
    yaxis={"title": "Power [dB]"},
    title={
        "text": "Autocorrelations",
        "xref": "paper",
        "x": 0.5,
        "font": {"size": 24},
    },
    autosize=True,
    showlegend=True,
    legend={"x": 1, "y": 1},
    margin={"l": 40, "b": 30, "r": 40, "t": 46},
    hovermode="closest",
)

dash_app.layout = html.Div(
    [dcc.Graph(figure=fig, id="autospectra", config={"doubleClick": "reset"},),],
)


@dash_app.callback(
    Output("autospectra", "figure"), [Input("autospectra", "relayoutData")]
)
def draw_undecimated_data(selection):
    if (
        selection is not None
        and "xaxis.range[0]" in selection
        and "xaxis.range[1]" in selection
        and len(
            df_full[
                (df_full.freqs >= selection["xaxis.range[0]"])
                & (df_full.freqs <= selection["xaxis.range[1]"])
            ]
        )
        < max_points
    ):
        x0 = selection["xaxis.range[0]"]
        x1 = selection["xaxis.range[1]"]

        new_fig = copy.deepcopy(fig)
        high_res = go.Figure()
        high_res["layout"] = new_fig["layout"]
        df1 = df_full[(df_full.freqs >= x0) & (df_full.freqs <= x1)]

        df1_down = df_down[(df_down.freqs >= x0) & (df_down.freqs <= x1)]

        for antpol in df_full.antpol.unique():
            df2 = df1[df1.antpol == antpol]

            trace = go.Scatter(
                x=df2.freqs,
                y=df2.spectra,
                name=antpol,
                mode="lines",
                hovertemplate="%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]",
            )
            high_res.add_trace(trace)

            df2 = df1_down[df_down.antpol == antpol]

            trace = go.Scatter(
                x=df2.freqs,
                y=df2.spectra,
                name=f"{antpol}-down",
                mode="markers",
                hovertemplate="%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]",
            )
            high_res.add_trace(trace)

    elif (
        selection is not None
        and "xaxis.range[0]" in selection
        and "xaxis.range[1]" in selection
        and len(
            df_full[
                (df_full.freqs >= selection["xaxis.range[0]"])
                & (df_full.freqs <= selection["xaxis.range[1]"])
            ]
        )
        >= max_points
    ):
        x0 = selection["xaxis.range[0]"]
        x1 = selection["xaxis.range[1]"]

        new_fig = copy.deepcopy(fig)
        high_res = go.Figure()
        high_res["layout"] = new_fig["layout"]
        df1 = df_down[(df_down.freqs >= x0) & (df_down.freqs <= x1)]
        for antpol in df_full.antpol.unique():
            df2 = df1[df1.antpol == antpol]

            trace = go.Scatter(
                x=df2.freqs,
                y=df2.spectra,
                name=antpol,
                mode="lines",
                hovertemplate="%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]",
            )
            high_res.add_trace(trace)

    else:
        high_res = copy.deepcopy(fig)
    return high_res
