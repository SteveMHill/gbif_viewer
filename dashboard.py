import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import polars as pl
import plotly.express as px
import plotly.figure_factory as ff

px.set_mapbox_access_token(open(".mapbox_token").read())

data = pl.read_parquet('data/dragonfly_small.parquet', columns=["gbifID","occurrenceID","country","genus","decimalLatitude","decimalLongitude"])
region = data.select(pl.col("country")).unique().to_series().to_list()
region.append('All')
region.sort()


app = dash.Dash(__name__, )
app.layout = html.Div([
                html.Div([
                    html.H3('Dragonfly Database', style = {"margin-bottom": "0px", 'color': 'black'}),
                ]),
                html.Div([
                    html.P('Select Region:', className = 'fix_label', style = {'color': 'black'}),
                    dcc.Dropdown(region, 'All', id='country'),

                ]),
                html.Div([
                    dcc.Graph(id = 'map',config = {'displayModeBar': 'hover'},style={'height': '700px'}),
                ]),

                html.Div([
                    dcc.Graph(id = 'bar_line_1',config = {'displayModeBar': 'hover'}),
                ]),
], id = "mainContainer", style = {"display": "flex", "flex-direction": "column"})

@app.callback(Output('bar_line_1', 'figure'),
    [Input('country', 'value')])

def update_graph(country):
    if country == "All":
        df = data
        occ_number = len(df)
        npc = df.group_by(pl.col("country")).len().sort(by="len", descending=True)
        barfig = px.bar(npc, x='country', y='len',labels={'len':'Number of occurrences','country':'Country'}, log_y=True, title=f"{occ_number} occurrences in total")
    else:
        df = data.filter(pl.col("country") == country)
        occ_number = len(df)
        spc = df.group_by(pl.col("genus")).len().sort(by= "len", descending=True)
        barfig = px.bar(spc, x='genus', y='len',labels={'len':'Number of occurrences','genus':'Genus'}, title=f"{occ_number} occurrences in total")

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
