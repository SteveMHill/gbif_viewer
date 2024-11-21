import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import polars as pl
import plotly.express as px
import plotly.figure_factory as ff
import dash_bootstrap_components as dbc

px.set_mapbox_access_token(open(".mapbox_token").read())

data = pl.read_parquet('data/dragonfly_small.parquet', columns=["gbifID","occurrenceID","country","genus","decimalLatitude","decimalLongitude"])
region = data.select(pl.col("country")).unique().to_series().to_list()
region.append('All')
region.sort()


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

SIDEBAR_STYLE = {
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "20rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

controls = dbc.Card([
            html.Div([
                html.Img(src="./assets/gce_logo.png",style={'height':'30%', 'width':'30%'}),
                html.H2('Dragonfly Database', style = { 'color': 'black'}),
                html.P('Select Region:',  style = {'color': 'black'}),
                 dcc.Dropdown(region, 'All', id='country'),
            ]),
        ], style = SIDEBAR_STYLE)

content =  html.Div([
                 dbc.Row([html.H4(id='number')],style={"height": "5vh"}),
                 dbc.Row([dcc.Graph(id = 'map',config = {'displayModeBar': 'hover'})], style={"height": "70vh"}),
                 dbc.Row([dcc.Graph(id = 'bar_line_1',config = {'displayModeBar': 'hover'})],style={"height": "25vh"}),
            ])

app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([html.Div([controls])], md=3),
            dbc.Col([html.Div([content])], md=9),
        ]),
        ],
        fluid=True,
    )

@app.callback(
    Output(component_id='number', component_property='children'),
    Input(component_id='country', component_property='value')
)
def update_output_div(country):
    if country == "All":
        df = data
        occ_number = len(df)
    else:
        df = data.filter(pl.col("country") == country)
        occ_number = len(df)
    return f'Occurrences: {occ_number}'

@app.callback(Output('bar_line_1', 'figure'),
    [Input('country', 'value')])

def update_graph(country):
    if country == "All":
        df = data
        occ_number = len(df)
        npc = df.group_by(pl.col("country")).len().sort(by="len", descending=True)
        barfig = px.bar(npc, x='country', y='len',labels={'len':'Number of occurrences','country':'Country'}, log_y=True)
    else:
        df = data.filter(pl.col("country") == country)
        occ_number = len(df)
        spc = df.group_by(pl.col("genus")).len().sort(by= "len", descending=True)
        barfig = px.bar(spc, x='genus', y='len',labels={'len':'Number of occurrences','genus':'Genus'})

    return barfig

@app.callback(Output('map', 'figure'),
    [Input('country', 'value')])
def update_map(country):
    if country == "All":
        df = data
        mapfig = ff.create_hexbin_mapbox(
            data_frame=df, lat="decimalLatitude", lon="decimalLongitude",
            nx_hexagon=150, zoom=4,opacity=0.4, range_color = [1,100],min_count= 3, labels={"color": "Point Count"},color_continuous_scale='turbo',
        )
    else:
        df = data.filter(pl.col("country") == country)
        mapfig = ff.create_hexbin_mapbox(
                data_frame=df, lat="decimalLatitude", lon="decimalLongitude",
                nx_hexagon=50,opacity=0.4,min_count= 1, labels={"color": "Point Count"},color_continuous_scale='turbo',
            )
    return mapfig


if __name__ == '__main__':
    app.run_server(debug = True)
