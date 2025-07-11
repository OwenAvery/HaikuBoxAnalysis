from dash import Dash, html, dash_table, dcc, Input, Output, State
import pandas as pd
import plotly.express as px
import base64
import io

app = Dash()

# ============
# Load + Clean
# ============
def parse_contents(contents):
    import base64
    import io
    import pandas as pd

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), 
                     usecols=["Species", "Local Date", "Local Time", "Score", "Count"], 
                     header=1)

    # Convert Count and Score to numeric
    df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0)
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0)

    # Drop rows with missing critical data
    df = df.dropna(subset=["Species", "Score", "Local Date", "Local Time"])

    # Parse Local Date with exact format matching your data (e.g. 29-Jun-2025)
    df["Local Date"] = pd.to_datetime(df["Local Date"], format="%d-%b-%Y", errors="coerce")

    # Parse Local Time - format is HH:MM:SS
    df["Local Time"] = pd.to_datetime(df["Local Time"], format="%H:%M:%S", errors="coerce").dt.time

    # Combine date and time into a datetime column
    df["DateTime"] = df.apply(lambda row: pd.Timestamp.combine(row["Local Date"], row["Local Time"]), axis=1)

    return df

# ============
# Layout
# ============
app.layout = html.Div([
    html.H1("Haikubox Bird Data Viewer"),

    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload CSV'),
        multiple=False
    ),

    html.Div([
        html.Label("Minimum Score:"),
        dcc.Slider(id='score-slider', min=0, max=1, step=0.05, value=0.5,
                   marks={0: '0', 0.5: '0.5', 1: '1'})
    ], style={"margin": "20px"}),

    html.Div([
        html.Label("Rarity Threshold (Max Sightings):"),
        dcc.Input(id='rarity-input', type='number', value=10, min=1, step=1),
    ], style={"margin": "20px"}),

    html.Div([
    html.Label("Select Month:"),
    dcc.Dropdown(
        id='month-dropdown',
        options=[
            {'label': 'All Months', 'value': 'All'},
            {'label': 'January', 'value': 'January'},
            {'label': 'February', 'value': 'February'},
            {'label': 'March', 'value': 'March'},
            {'label': 'April', 'value': 'April'},
            {'label': 'May', 'value': 'May'},
            {'label': 'June', 'value': 'June'},
            {'label': 'July', 'value': 'July'},
            {'label': 'August', 'value': 'August'},
            {'label': 'September', 'value': 'September'},
            {'label': 'October', 'value': 'October'},
            {'label': 'November', 'value': 'November'},
            {'label': 'December', 'value': 'December'},
        ],
        value='All',  # default value
        clearable=False,
        style={"width": "200px"}
    )
    ], style={"margin": "20px"}),

    html.H2("Top 20 Most Common Bird Species"),
    dcc.Graph(id='top-graph'),

    html.H2("Rare Species List"),
    html.Ul(id='rare-list'),
    dcc.Graph(id='rare-bar-chart'),

    html.H2("Bird Activity Heatmap"),
    dcc.Graph(id='heatmap-graph')
])

# =============
# All-in-one callback
# =============
@app.callback(
    Output('top-graph', 'figure'),
    Output('rare-bar-chart', 'figure'),
    Output('rare-list', 'children'),
    Output('heatmap-graph', 'figure'),
    Input('upload-data', 'contents'),
    Input('score-slider', 'value'),
    Input('rarity-input', 'value'),
    Input('month-dropdown', 'value')
)
def update_dashboard(contents, min_score, rarity_threshold, selected_month):
    if contents is None:
        # Return empty graphs when no data uploaded
        empty_fig = px.bar(title="Upload a CSV file to see data")
        return empty_fig, empty_fig, [], empty_fig

    df = parse_contents(contents)

    # Filter by selected month if not 'All'
    if selected_month != "All":
        print("Available months in data:", df["Local Date"].dt.month_name().unique())
        print(df["Local Date"].dt.month_name().unique())
        print(f"Selected month: {selected_month}")
        df = df[df["Local Date"].dt.month_name() == selected_month]
        print(df)

    if df.empty:
        empty_fig = px.bar(title="No data for selected month")
        return empty_fig, empty_fig, [html.Li("No data available for selected month")], empty_fig

    # Filter by minimum score
    filtered_df = df[df["Score"] >= min_score]

    # Top 20 species
    top_counts = filtered_df.groupby("Species", as_index=False)["Count"].sum()
    top_counts = top_counts.sort_values("Count", ascending=False).head(20)
    top_fig = px.bar(top_counts, x="Count", y="Species", orientation="h",
                     title="Top 20 Most Common Bird Species")
    top_fig.update_layout(yaxis=dict(categoryorder='total ascending'))

    # Rare species list & graph
    rare_counts = filtered_df.groupby("Species", as_index=False)["Count"].sum()
    rare_counts = rare_counts[rare_counts["Count"] <= rarity_threshold].sort_values("Count")
    rare_fig = px.bar(rare_counts, x="Count", y="Species", orientation="h",
                      title=f"Rare Birds (Score ≥ {min_score}, Sightings ≤ {rarity_threshold})")
    rare_fig.update_layout(yaxis=dict(categoryorder='total ascending'), height=500)
    rare_list = [html.Li(f"{row['Species']}: {int(row['Count'])} sightings") for _, row in rare_counts.iterrows()]

    # Bird activity heatmap
    df["Hour"] = df["DateTime"].dt.hour
    df["Weekday"] = df["DateTime"].dt.day_name()
    activity = df[df["Score"] >= min_score].groupby(["Weekday", "Hour"])["Count"].sum().reset_index()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    activity["Weekday"] = pd.Categorical(activity["Weekday"], categories=weekday_order, ordered=True)
    activity = activity.sort_values(["Weekday", "Hour"])

    heatmap_fig = px.density_heatmap(
        activity, x="Hour", y="Weekday", z="Count",
        color_continuous_scale="Viridis",
        title="Bird Activity by Hour and Weekday"
    )
    heatmap_fig.update_layout(height=500)

    return top_fig, rare_fig, rare_list, heatmap_fig

# ============
# Run
# ============
if __name__ == '__main__':
    app.run(debug=True)
