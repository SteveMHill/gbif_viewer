import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import polars as pl
import plotly.express as px
import plotly.figure_factory as ff
import dash_bootstrap_components as dbc
import os


def get_mapbox_token():
    if os.environ.get("MAPBOX_TOKEN", None):
        return os.environ["MAPBOX_TOKEN"]
    elif os.path.exists(".mapbox_token"):
        with open(".mapbox_token", "rt") as f:
            return f.read().strip()
    else:
        raise ValueError(
            "Could not load mapbox token\n"
            "Either set the MAPBOX_TOKEN environment variable to your token string \n"
            "or create a file named .mapbox_token containing your token in the\n"
            "top-level project directory"
        )

# the style arguments for the sidebar.
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "height": "100%",
    "z-index": 1,
    "overflow-x": "hidden",
    "transition": "all 0.5s",
    "padding": "0.5rem 1rem",
    "background-color": "#f8f9fa",
}

# the style arguments for the main content page.
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "4rem 1rem 2rem",
}

TEXT_STYLE = {
    'textAlign': 'center',
    'color': '#191970'
}

CARD_TEXT_STYLE = {
    'textAlign': 'center',
    'color': '#0074D9'
}

mt = get_mapbox_token()
px.set_mapbox_access_token(mt)

data = pl.read_parquet('data/dragonfly_database.parquet', columns=["gbifID","occurrenceID","country","Region","species","publisher","basisOfRecord","genus","sex","decimalLatitude","decimalLongitude"])
data = data.rename({"species": "Species", "genus": "Genus", "sex":"Sex", "publisher":"Publisher"})
region = data.select(pl.col("country")).unique().to_series().to_list()
region.append('All')
region.sort()

vari = ["Region","Species", "Genus", "Sex","basisOfRecord","Publisher"]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
controls = html.Div(
            [
                html.P('Select Region', style={'textAlign': 'center'}),
                dcc.Dropdown(region,  value='All', id='country'),
                html.Br(),
                html.P('Variable', style={'textAlign': 'center'}),
                dcc.Dropdown(vari,  value='Region', id='para'),
                html.Br(),
                html.P('HexSize', style={'textAlign': 'center'}),
                dcc.Slider(50, 300, 50, value=100,id='hexsize'),
            ])

sidebar = html.Div(
    [
          html.H2('Parameters', style=TEXT_STYLE),
          html.Hr(),
          controls
            ],style = SIDEBAR_STYLE)

card_row = dbc.Row([
    dbc.Col(
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4("Occurences",style=CARD_TEXT_STYLE),
                        html.P(id='number', style=CARD_TEXT_STYLE),
                    ]
                )
            ]
        ),
        md=6
    ),
    dbc.Col(
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4("Species",style=CARD_TEXT_STYLE),
                        html.P(id='species_number', style=CARD_TEXT_STYLE),
                    ]
                )
            ]
        ),
        md=6
    ),
])

first_row = dbc.Row(
    [
        dbc.Col(
             dcc.Graph(id = 'map',config = {'displayModeBar': 'hover','scrollZoom': True},style={"height": 500}),md=12,
        )
    ],
)

second_row = dbc.Row(
    [
        dbc.Col(
            dcc.Graph(id = 'bar_line_1',config = {'displayModeBar': 'hover'}), md=12,
        )
    ]
)


content = dbc.Container(
    [
        #html.H2('Dragonfly Dashboard', style=CARD_TEXT_STYLE),
        #html.Hr(),
        card_row,
        first_row,
        second_row,
    ],
    style=CONTENT_STYLE
)

app.layout = html.Div([sidebar, content])

@app.callback(
    Output(component_id='number', component_property='children'),
    Input(component_id='country', component_property='value')
)
def update_number(country):
    if country == "All":
        df = data
        occ_number = len(df)
    else:
        df = data.filter(pl.col("country") == country)
        occ_number = len(df)
    return f'{occ_number}'

@app.callback(
    Output(component_id='species_number', component_property='children'),
    Input(component_id='country', component_property='value')
)
def update_species(country):
    if country == "All":
        df = data
        spc_number = len(df.unique(subset="Species"))
    else:
        df = data.filter(pl.col("country") == country)
        spc_number = len(df.unique(subset="Species"))
    return f'{spc_number}'

@app.callback(Output('bar_line_1', 'figure'),
    [Input('country', 'value')],
    [Input('para', 'value')])
def update_graph(country, para):
    if country == "All":
        if para == "Region":
            npc = data.group_by(pl.col("country")).len().sort(by="len", descending=True)
            barfig = px.bar(npc, x="country", y='len',labels={'len':'Number of occurrences'}, log_y=False)
        else:
            npc = data.group_by(pl.col(para)).len().sort(by="len", descending=True)
            barfig = px.bar(npc, x=para, y='len',labels={'len':'Number of occurrences'}, log_y=False)
    else:
        df = data.filter(pl.col("country") == country)
        spc = df.group_by(pl.col(para)).len().sort(by= "len", descending=True)
        barfig = px.bar(spc, x=para, y='len',labels={'len':'Number of occurrences'})
    return barfig

@app.callback(Output('map', 'figure'),
    [Input('country', 'value')],
    [Input('hexsize', 'value')])
def update_map(country, hexsize):
    if country == "All":
        df = data
        mapfig = ff.create_hexbin_mapbox(
            data_frame=df, lat="decimalLatitude", lon="decimalLongitude",
            nx_hexagon=hexsize, zoom=2,opacity=0.4, range_color = [1,100],min_count= 3, labels={"color": "Point Count"},color_continuous_scale='turbo',
        )
    else:
        df = data.filter(pl.col("country") == country)
        mapfig = ff.create_hexbin_mapbox(
                data_frame=df, lat="decimalLatitude", lon="decimalLongitude",
                nx_hexagon=hexsize,opacity=0.4,min_count= 1, labels={"color": "Point Count"},color_continuous_scale='turbo',
            )
    return mapfig


if __name__ == '__main__':
    app.run_server(debug = True)
