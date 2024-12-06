import dash
from dash import dcc, html, Input, Output, State, _dash_renderer
import plotly.express as px
import plotly.figure_factory as ff
import polars as pl
import dash_mantine_components as dmc
import os
_dash_renderer._set_react_version("18.2.0")

# Helper Functions
def get_mapbox_token():
    """Load the Mapbox token from environment variables or a local file."""
    if os.environ.get("MAPBOX_TOKEN"):
        return os.environ["MAPBOX_TOKEN"]
    elif os.path.exists(".mapbox_token"):
        with open(".mapbox_token", "rt") as f:
            return f.read().strip()
    else:
        raise ValueError(
            "Could not load Mapbox token. Set MAPBOX_TOKEN or create a .mapbox_token file."
        )


def load_data():
    """Load and preprocess the dataset."""
    data = pl.read_parquet("./data/dragonfly_database.parquet",
        columns=["gbifID", "occurrenceID", "country", "species", "lifeStage", "sex", "publisher",
                 "basisOfRecord", "decimalLatitude", "decimalLongitude", "coordinateUncertaintyInMeters"]
    )
    data = data.rename({
        "species": "Species",
        "sex": "Sex",
        "lifeStage": "LifeStage",
        "publisher": "Publisher",
        "country": "Country",
        "coordinateUncertaintyInMeters" : "Uncertainty"
    })
    data = data.with_columns(
    [
        pl.col("LifeStage").cast(str),
        pl.col("Sex").cast(str),
        pl.col("Species").cast(str)
    ]
    )
    return data


# Configuration
MAPBOX_TOKEN = get_mapbox_token()
px.set_mapbox_access_token(MAPBOX_TOKEN)

data = load_data()
regions = ["All"] + sorted(data["Country"].unique().to_list())
life_stages = ["All"] + sorted(data["LifeStage"].fill_null("Unknown").unique().to_list())
#life_stages = ['None' if ls is None else ls for ls in life_stages]
sex_options = ["All"] + sorted(data["Sex"].fill_null("Unknown").unique().to_list())
#sex_options = ['None' if ls is None else ls for ls in sex_options]
species_options = ["All"] + sorted(data["Species"].fill_null("Unknown").unique().to_list())
#species_options = ['None' if ls is None else ls for ls in species_options]
variables = ["Country", "Species", "Sex", "LifeStage", "Publisher"]

# App Initialization
app = dash.Dash(__name__, external_stylesheets=dmc.styles.ALL)
server = app.server

# Styles
STYLES = {
    "header": {
        "backgroundColor": "#007bff",
        "color": "white",
        "padding": "0.5rem",
        "textAlign": "center",
        "fontSize": "1.5rem",
        "fontWeight": "bold",
    },
    "row": {
        "display": "flex",
        "flexDirection": "row",
        "alignItems": "stretch",
        "gap": "1rem",
        "marginBottom": "2rem",
    },
    "box": {
        "flex": 1,
        "padding": "1rem",
        "backgroundColor": "#f8f9fa",
        "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
        "borderRadius": "8px",
    },
    "controls": {
        "width": "20rem",
        "padding": "1rem",
        "backgroundColor": "#f1f3f5",
        "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
        "borderRadius": "8px",
    },
}

# Layout Components
def create_map_controls():
    """Creates control elements for region, life stage, sex, hexbin, and species."""
    return dmc.Stack(
        mt="md",
        children=[
            dmc.MultiSelect(
                data=[{"value": ls, "label": ls} for ls in regions],
                value=[],  # Start empty
                id="country",
                label="Select Region(s)",
                placeholder="All",
                clearable=True,
            ),
            dmc.Select(
                data=[{"value": ls, "label": ls} for ls in life_stages],
                value="All",
                id="life_stage",
                label="Select Life Stage",
            ),
            dmc.Select(
                data=[{"value": s, "label": s} for s in sex_options],
                value="All",
                id="sex",
                label="Select Sex",
            ),
            dmc.Select(
                data=[{"value": s, "label": s} for s in species_options],
                id="species",
                label="Select Species",
            ),
            dmc.Select(
                            data=[
                                {"value": "1", "label": "<=1"},
                                {"value": "10", "label": "<=10"},
                                {"value": "50", "label": "<=50"},
                                {"value": "100", "label": "<=100"},
                                {"value": "500", "label": "<=500"},
                                {"value": "1000", "label": "<=1000"}
                            ],
                            value=1000,  # Default to 1000
                            id="uncertainty",
                            label="Select Uncertainty (m)",
                        ),
            dmc.Text("Select number of HexBins", size="sm"),
            dmc.Slider(
                value=100,
                min=50,
                max=200,
                  marks=[
                      {"value": 50, "label": "50"},
                      {"value": 100, "label": "100"},
                      {"value": 150, "label": "150"},
                      {"value": 200, "label": "200"},
                  ],
                  id="hexsize",
                  label="HexBin Size",

            ),
        ],
    )


def create_graph_controls():
    """Creates control elements for variable selection."""
    return dmc.Select(
        data=[{"value": str(v), "label": str(v)} for v in variables],
        value="Country",
        id="para",
        label="Variable Selection",
    )


# Layout
app.layout = dmc.MantineProvider([html.Div(
    style={"padding": "2rem"},
    children=[
        html.Div("Dragonfly Database", style=STYLES["header"]),
        html.Div(
            style=STYLES["row"],
            children=[
                html.Div(
                    style=STYLES["controls"],
                    children=create_map_controls(),
                ),
                html.Div(
                    style=STYLES["box"],
                    children=[
                        html.Div(id="occurrences_card", style={"marginBottom": "1rem"}),
                        dcc.Graph(
                            id="map",
                            config={"displayModeBar": "hover", "scrollZoom": True},
                            style={"height": "500px"},
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            style=STYLES["row"],
            children=[
                html.Div(
                    style=STYLES["controls"],
                    children=create_graph_controls(),
                ),
                html.Div(
                    style=STYLES["box"],
                    children=[
                        dcc.Graph(
                            id="bar_line_1",
                            config={"displayModeBar": "hover"},
                            style={"height": "400px"},
                        ),
                    ],
                ),
            ],
        ),
    ],
),
],
)


# Callbacks
@app.callback(
    Output("occurrences_card", "children"),
    Input("country", "value"),
    Input("life_stage", "value"),
    Input("sex", "value"),
    Input("species", "value"),
    Input("uncertainty", "value")
)
def update_occurrences_card(country, life_stage, sex, species, uncertainty):
    """Update the occurrences card based on the selected region and filters."""
    df = data
    if country and country != "All":
        df = df.filter(pl.col("Country").is_in(country))
    if life_stage and life_stage != "All":
        df = df.filter(pl.col("LifeStage") == life_stage)
    if sex and sex != "All":
        df = df.filter(pl.col("Sex") == sex)
    if species and species != "All":
        df = df.filter(pl.col("Species") == species)
    if uncertainty:
        df = df.filter(pl.col("Uncertainty") <= int(uncertainty))  # Convert string to int for comparison

    return f"Occurrences: {len(df)}"

@app.callback(
    Output("map", "figure"),
    Input("country", "value"),
    Input("life_stage", "value"),
    Input("sex", "value"),
    Input("species", "value"),
    Input("hexsize", "value"),
    Input("uncertainty", "value")  # Add uncertainty as an input
)
def update_map(country, life_stage, sex, species, hexsize, uncertainty):
    df = data
    if country and country != "All":
        df = df.filter(pl.col("Country").is_in(country))
    if life_stage and life_stage != "All":
        df = df.filter(pl.col("LifeStage") == life_stage)
    if sex and sex != "All":
        df = df.filter(pl.col("Sex") == sex)
    if species and species != "All":
        df = df.filter(pl.col("Species") == species)
    if uncertainty:
        df = df.filter(pl.col("Uncertainty") <= int(uncertainty))  # Convert string to int for comparison

    return ff.create_hexbin_mapbox(
        data_frame=df,
        lat="decimalLatitude",
        lon="decimalLongitude",
        nx_hexagon=int(hexsize),
        opacity=0.4,
        min_count=1,
        labels={"color": "Point Count"},
        color_continuous_scale="turbo",
    )


@app.callback(
    Output("bar_line_1", "figure"),
    Input("country", "value"),
    Input("life_stage", "value"),
    Input("sex", "value"),
    Input("species", "value"),
    Input("para", "value"),
    Input("uncertainty", "value")  # Add uncertainty as an input
)
def update_graph(country, life_stage, sex, species, para, uncertainty):
    df = data
    if country and country != "All":
        df = df.filter(pl.col("Country").is_in(country))
    if life_stage and life_stage != "All":
        df = df.filter(pl.col("LifeStage") == life_stage)
    if sex and sex != "All":
        df = df.filter(pl.col("Sex") == sex)
    if species and species != "All":
        df = df.filter(pl.col("Species") == species)
    if uncertainty:
        df = df.filter(pl.col("Uncertainty") <= int(uncertainty))  # Convert string to int for comparison

    # Example graph generation based on the selected parameter
    grouped = df.group_by(para).agg(pl.col("occurrenceID").count().alias("count"))
    fig = px.bar(grouped.to_pandas(), x=para, y="count", title=f"{para} Occurrences")
    return fig

@app.callback(
    Output("species", "data"),
    Output("life_stage", "data"),
    Output("sex", "data"),
    Input("country", "value"),
    Input("life_stage", "value"),
    Input("sex", "value"),
    Input("uncertainty", "value")  # Add uncertainty as an input
)
def update_selection_options(country, life_stage, sex, uncertainty):
    """Dynamically update species, life stage, and sex options based on filters."""
    df = data

    # Filter data based on the selected country, life stage, sex, and uncertainty
    if country and country != "All":
        df = df.filter(pl.col("Country").is_in(country))
    if life_stage and life_stage != "All":
        df = df.filter(pl.col("LifeStage") == life_stage)
    if sex and sex != "All":
        df = df.filter(pl.col("Sex") == sex)
    if uncertainty:
        df = df.filter(pl.col("Uncertainty") <= int(uncertainty))  # Convert string to int for comparison

    # Update species options: replace None with 'Unknown' and sort
    species_options = sorted(df["Species"].fill_null("Unknown").unique().to_list())
    species_data = [{"value": s, "label": s} for s in species_options] + [{"value": "All", "label": "All"}]

    # Update life stage options: replace None with 'Unknown' and sort
    life_stage_options = sorted(df["LifeStage"].fill_null("Unknown").unique().to_list())
    life_stage_data = [{"value": s, "label": s} for s in life_stage_options] + [{"value": "All", "label": "All"}]

    # Update sex options: replace None with 'Unknown' and sort
    sex_options = sorted(df["Sex"].fill_null("Unknown").unique().to_list())
    sex_data = [{"value": s, "label": s} for s in sex_options] + [{"value": "All", "label": "All"}]

    return species_data, life_stage_data, sex_data


# Start Server
if __name__ == "__main__":
    app.run_server(debug=True)
