import numpy as np
from plotly.offline import plot
import plotly.graph_objs as go


def make_plot(stats):
    fig = go.Figure()
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
    for stat in stats:
        spectra = 10 * np.log10(np.ma.masked_invalid(stat.spectra))
        fig.add_trace(
            go.Scatter(
                x=np.asarray(stat.frequencies) / 1e6,
                y=spectra.filled(None),
                mode="lines",
                name=f"{stat.antenna.ant_number}{stat.antenna.polarization}",
                hovertemplate="%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]",
            )
        )

    return fig.to_html(include_plotlyjs=False, full_html=False)
